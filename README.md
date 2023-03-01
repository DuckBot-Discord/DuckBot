# Hello, I'm [DuckBot](https://top.gg/bot/788278464474120202 "top.gg/bot/788278464474120202") 💞

This is DuckBot's source code. Invite me using the hyperlink above.

## Hosting locally

1. Install python 3.11 on your machine.
2. Create a file called `.env`.
3. Put the contents of `.env.example` in it and fill out the information as needed. (some fields are optional).
4. Create a database and user for the database, and run the `pg_dump.sql` file to create the required tables.
5. Install the requirements from `requirements.txt`.
6. Run the bot: `python bot.py`.

> **Note**
> Using a [virtual environment](https://docs.python.org/3/library/venv.html) is recommended.

> **Warning**: lru-dict installation errors.
>
> the `lru_dict` requirement may need you to install the `python-dev` package on linux (use the appropriate one for 
> your python version), or [Microsoft Visual C++](https://web3py.readthedocs.io/en/v5/troubleshooting.html?#why-am-i-getting-visual-c-or-cython-not-installed-error)
> on windows.

## Contributing

Thanks for taking an interest in contributing to DuckBot! The only thing I ask for is that you test
the changes locally before making a pull request. Use python 3.11.2

> **Warning**: Legacy code base.
>
> Currently, the main focus of the project is the [`branch:rewrite`](https://github.com/DuckBot-Discord/DuckBot/tree/rewrite).
> The [`branch:master`](https://github.com/DuckBot-Discord/DuckBot/tree/master) is "legacy" meaning I am only doing bug fixes there as it's not my main focus.
> If you wish to truly partake in the development of duckbot's rewrite, I highly recommend you join our [support server](https://discord.gg/TdRfGKg8Wh) and I will
> help you get started with it.

