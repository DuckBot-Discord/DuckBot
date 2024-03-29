<!-- This file is a modified version of the following file:                   -->
<!-- https://github.com/Rapptz/discord.py/blob/master/.github/CONTRIBUTING.md -->
# Contributing to DuckBot Rewrite

First off, thanks for taking the time to contribute. It makes the library substantially better. :+1:

The following is a set of guidelines for contributing to the repository. These are guidelines, not hard rules.

> **Warning**
>
> The production version of this code can be located at [`branch:master`](https://github.com/DuckBot-Discord/DuckBot/tree/master). If you're looking to submit a bugfix you found in the bot, target [`branch:master`](https://github.com/DuckBot-Discord/DuckBot/tree/master) instead.

## Good Bug Reports

Please be aware of the following things when filing bug reports.

1. Don't open duplicate issues. Please search your issue to see if it has been asked already. Duplicate issues will be closed.
2. When filing a bug about exceptions or tracebacks, please include the *complete* traceback. This will allow us to see where in the code base the error happened.
3. Make sure to provide enough information to make the issue workable.
    - A **summary** of your bug report. This is generally a quick sentence or two to describe the issue in human terms.
    - Guidance on **how to reproduce the issue**. Let us know what the steps were, how often it happens, etc.
    - Tell us **what you expected to happen**. That way we can meet that expectation.
    - Tell us **what actually happens**. What ends up happening in reality? It's not helpful to say "it fails" or "it doesn't work". Say *how* it failed, do you get an exception? Does it hang? How are the expectations different from reality?
    - Tell us **information about your environment**. What operating system are you running on? Are the installed requirements up-to-date? These are valuable questions and information that we use.

If the bug report is missing this information then it'll take us longer to fix the issue. We will probably ask for clarification, and barring that if no response was given then the issue will be closed.

## Submitting a Pull Request

Submitting a pull request is fairly simple, just make sure it focuses on a single aspect and doesn't manage to have scope creep and it's probably good to go. It would be incredibly lovely if the style is consistent to that found in the project. This project follows PEP-8 guidelines (mostly) with a column limit of 125. We strive to have everything documented so that the code is self-explainatory.

### Git Commit Guidelines

- Use present tense (e.g. "Add feature" not "Added feature")
- Limit all lines to 72 characters or less.
- Reference issues or pull requests outside of the first line.
- Please use the shorthand `#123` and not the full URL.

If you do not meet any of these guidelines, don't fret. Chances are they will be fixed upon rebasing but please do try to meet them to remove some of the workload.
