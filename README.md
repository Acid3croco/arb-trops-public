# arb-trops-phoenix

Crypto trading framework written in Python, using redis as message broker & state and postgresql as database.

# USAGE

Small usage of feed_handler system

## Load codes

Load referential in DB for BYBIT

```
load_codes -e BYBIT
```

## Feed Handler

Start feed handler for BYBIT

```
start_fh -C l2_book trades -e BYBIT -t perpetual -c linear inverse -b BTC ETH
```

## Show book or trades

```
smb BTC -c linear inverse
```

```
trades --trades -e BYBIT -t perpetual -b BTC ETH
```

# INSTALL

You can use a venv if you want.

## requirements

- You need to install psycopg2 first for DB to work.
- Then install the rest of the requirements.

```
pip install -e requirements.txt

```

## Standalone repos

If you want to use the original repos, you can install them with:

I use custom fork of `cryptofeed` (for more exchanges) and `polo-futures-sdk-python` are used (for load_codes).

Choose one of the following:

```
pip install cryptofeed
```

OR

```
git clone git@github.com:Acid3croco/cryptofeed.git
cd cryptofeed
pip install -e ./
```

And then install `polo-futures-sdk-python` :

```
git clone https://github.com/poloniex/polo-futures-sdk-python.git
cd polo-futures-sdk-python
pip install -e ./
```

# SETUP

## Arb Packages

Use the `manage_packages.py` script in `packages/` to install arb packages

## Redis

```
redis-server &
```

## Database

Timescale dockerised database

### Basic commands

Create DB:

```
docker-compose up --build -d
```

Show logs:

```
docker-compose logs -f --tail=1000 db
```

Connect to DB:

```
docker-compose exec db psql arb_trops_db arb_trops
```

Backup DB:

```
docker exec -t <container*id> pg_dumpall -c -U arb_trops > dump_arb_trops*`date +%d-%m-%Y`.sql
```

Restore DB:

```
docker exec -i <container_id> psql -U arb_trops -d arb_trops_db < dump_arb_trops_28-01-2022.sql
```

Delete the DB:

```
docker-compose down -v --remove-orphans
```

## Working with fields

To update database schema, we will change the schema `arb_trops.sql` file, and use `pwiz` script from `peewee` package to update the ORM models.

When your `.sql` file is updated, you have to down and up the docker of the database.

Now your database is loaded with your new schema. Last step is to update the ORM models:

```
$ python -m pwiz -H localhost -u arb_trops -P -o arb_trops_db > db_models.py
```

You now have up to date ORM models to work with.

## Redis cheat sheet

In terminal

```
redis-cli --intrinsic-latency 100
```

Inside `redis-cli`

```
CONFIG SET latency-monitor-threshold 1 (in ms)
CONFIG SET slowlog-log-slower-than 3000 (in µs)
LATENCY DOCTOR
LATENCY RESET
INFO
INFO STATS
SLOWLOG GET
```

# Arb SERVICE to manage SETUP

### Launch arb-trops services

```
SERVICE_arb start
```

### Stop arb-trops services

```
SERVICE_arb stop
```

### Stop arb-trops services and clean db

```
SERVICE_arb force-stop
```

### Status arb-trops services

```
SERVICE_arb status
```

# Git stats

```
git log --stat-count=1 | grep 'files changed' | head -n 12
```

```
git-fame --excl="(json)|(sql)|(csv)"
```

```
cloc ./ --not-match-f="(json)|(sql)|(csv)" --exclude-dir=miscs
```

can also use `scc` if installed instead of `cloc`
