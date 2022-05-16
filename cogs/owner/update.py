from dataclasses import dataclass
import importlib
import re
import traceback
from typing import List, Optional
from utils import DuckCog, DuckContext, Shell, group
from jishaku.paginators import WrappedPaginator
from discord.ext.commands import ExtensionNotLoaded, ExtensionNotFound, NoEntryPointError, Paginator


FILENAME_PATTERN = re.compile('\\s*(?P<filename>.+?)\\s*\\|\\s*[0-9]+\\s*[+-]+')
COGS_PATTERN = re.compile('cogs\\/\\w+\\/|cogs\\/\\w+\\.py')


@dataclass()
class Module:
    path: str
    exception: Optional[Exception] = None

    @property
    def is_cog(self):
        return self.name.startswith('cogs.')

    @property
    def name(self) -> str:
        match = COGS_PATTERN.match(self.path)
        if match:
            return match.group()[0].replace('/', '.').removeprefix('.py').rstrip('.')
        return self.path.replace('/', '.').removeprefix('.py').rstrip('.')

    @property
    def failed(self):
        return self.exception is not None


def fmt(exc: Exception) -> str:
    lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    return ''.join(lines)


def wrap(text: str, language: str = 'py') -> List[str]:
    paginator = WrappedPaginator(prefix=f'```{language}' + language, suffix='```', force_wrap=True)
    for line in text.splitlines():
        paginator.add_line(line)
    return paginator.pages


class ExtensionsManager(DuckCog):
    def find_modules_to_reload(self, output: str) -> List[Module]:
        """Returns a dictionary of filenames to module names to reload."""
        return [Module(path=m) for m in FILENAME_PATTERN.findall(output)]

    async def try_reload(self, name: str):
        try:
            await self.bot.reload_extension(name)
            return "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}"
        except ExtensionNotLoaded:
            await self.bot.load_extension(name)
            return "\N{INBOX TRAY}"

    async def reload_to_page(self, extension, *, paginator: Paginator):
        try:
            emoji = await self.try_reload(extension)
            paginator.add_line(f'{emoji} `{extension}`')
        except NoEntryPointError:
            paginator.add_line(f'\N{CROSS MARK} `{extension}` (has no `setup` function)')
        except ExtensionNotFound:
            paginator.add_line(f'\N{BLACK QUESTION MARK ORNAMENT} `{extension}`')
        except Exception as e:
            paginator.add_line(f'\N{CROSS MARK} `{extension}`')
            paginator.add_line(f"```py\n{fmt(e)}\n```")

    @group(invoke_without_command=True)
    async def reload(self, ctx: DuckContext, *extensions: str):
        paginator = WrappedPaginator(prefix='', suffix='', force_wrap=True)
        for extension in extensions:
            await self.reload_to_page(extension, paginator=paginator)
        for page in paginator.pages:
            await ctx.send(page)

    @reload.command(name='git')
    async def reload_git(self, ctx: DuckContext):
        '''|coro|

        Updates the bot.

        This command will pull from github, and then reload the modules of the bot that have changed.
        '''
        shell = Shell('git pull')
        stdout = (await shell.run()).stdout

        modules = self.find_modules_to_reload(stdout)

        for module in sorted(modules, key=lambda m: m.is_cog, reverse=True):
            try:
                if module.is_cog:
                    emoji = await self.try_reload(module.name)
                    stdout.replace(module.path, f"{emoji} {module.path}")
                else:
                    m = importlib.import_module(module.name)
                    importlib.reload(m)
            except Exception as e:
                stdout.replace(module.path, f"\N{CROSS MARK} {module.path}")
                module.exception = e

        paginator = WrappedPaginator(prefix='', suffix='', force_wrap=True)
        for page in wrap(stdout, language='sh'):
            paginator.add_line(page)
        paginator.add_line()

        for module in filter(lambda m: m.failed, modules):
            assert module.exception is not None
            paginator.add_line(f"\N{WARNING SIGN} {module.path}")
            paginator.add_line(f"```py\n{fmt(module.exception)}\n```", empty=True)

        for page in paginator.pages:
            await ctx.send(page)

    @reload.command(name='all')
    async def reload_all(self, ctx: DuckContext):
        '''Reloads all extensions.'''
        paginator = WrappedPaginator(prefix='', suffix='', force_wrap=True)
        for extension in self.bot.extensions:
            await self.reload_to_page(extension, paginator=paginator)
        for page in paginator.pages:
            await ctx.send(page)

    @reload.command(name='module', aliases=['modules'])
    async def reload_module(self, ctx: DuckContext, *modules: str):
        '''Reloads a module.

        Parameters
        ----------
        module : str
            The module to reload.

        '''
        paginator = WrappedPaginator(prefix='', suffix='', force_wrap=True)
        for module in modules:
            try:
                m = importlib.import_module(module)
                importlib.reload(m)
                paginator.add_line(f"\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS} {module}")
            except Exception as e:
                paginator.add_line(f"\N{CROSS MARK} {module}")
                paginator.add_line(f"```py\n{fmt(e)}\n```", empty=True)
        for page in paginator.pages:
            await ctx.send(page)
