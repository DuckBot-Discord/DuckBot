# Hello, I'm [DuckBot](https://top.gg/bot/788278464474120202 "top.gg/bot/788278464474120202") 💞

This is DuckBot's source code. Invite me using the hyperlink above.

## Hosting locally

1. Install python 3.11 on your machine.
2. Create a `.env` file, in `/utils/.env`.
3. Put the contents of `/utils/example.env` in it and fill out the information as needed. (some fields are optional).
4. Create a PostgreSQL database and a user in it, then run the `schema.sql` file to create the required tables.
5. Install the requirements from `requirements.txt`.
6. Run the bot: `python .`. or to enable discord.py debug logs, `python . --verbose`

> **Note**
> Using a [virtual environment](https://docs.python.org/3/library/venv.html) is recommended.

> **Warning**: lru-dict installation errors.
>
> the `lru_dict` requirement may need you to install the `python-dev` package on linux (use the appropriate one for
> your python version), or [Microsoft Visual C++](https://web3py.readthedocs.io/en/v5/troubleshooting.html?#why-am-i-getting-visual-c-or-cython-not-installed-error)
> on windows.

## Contributing

Thanks for taking an interest in contributing to DuckBot! Please check out [the contributing guidelines](/.github/contributing.md)!

> **Note**: Rewrite code base (not production).
>
> The production code of this bot can be found in [`branch:master`](https://github.com/DuckBot-Discord/DuckBot/tree/master).
> If you are looking to submit a pull request to fix a bug in the current version of DuckBot, check out that branch instead!
