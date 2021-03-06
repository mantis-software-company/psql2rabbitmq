# psql2rabbitmq

psql2rabbitmq is a library that asynchronously forwards postgresql data to the RabbitMQ message queue in the requested template. Using the library, the parametrically given query is run, and the data obtained is converted into the format specified as a template and forwarded to the message queue.

## Installation

You can install this library easily with pip.
`pip install psql2rabbitmq` 

## DELETE_AFTER_QUERY mode
 
You can delete records from table after send to queue via setting `DELETE_AFTER_QUERY` environment variable to `True`.  You should set `DELETE_RECORD_COLUMN` environment variable to which column should be deleted which defined in select query for this. Example delete sql script should be this format:

```sql
DELETE FROM my_table WHERE my_column = %s -- %s is value for my_column which defined in select query. Don't quoute this parameter!  
```


## Usage
### As a library
```py
import os
import asyncio
from psql2rabbitmq import perform_task

if __name__ == '__main__':
    logger = logging.getLogger("psql2rabbitmq")
    logger.setLevel(os.environ.get('LOG_LEVEL', "DEBUG"))
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            os.environ.get('LOG_FORMAT', "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
    )
    logger.addHandler(handler)

    config = {
            "mq_host": os.environ.get('MQ_HOST'),
            "mq_port": int(os.environ.get('MQ_PORT', '5672')),
            "mq_vhost": os.environ.get('MQ_VHOST'),
            "mq_user": os.environ.get('MQ_USER'),
            "mq_pass": os.environ.get('MQ_PASS'),
            "mq_exchange": os.environ.get('MQ_EXCHANGE', 'psql2rabbitmq'),
            "mq_routing_key": os.environ.get('MQ_ROUTING_KEY', 'psql2rabbitmq'),
            "db_host": os.environ.get('DB_HOST'),
            "db_port": int(os.environ.get('DB_PORT', '5432')),
            "db_user": os.environ.get('DB_USER'),
            "db_pass": os.environ.get('DB_PASS'),
            "db_database": os.environ.get('DB_DATABASE'),
            "sql_file_path": os.environ.get('SQL_FILE_PATH'),
            "data_template_file_path": os.environ.get('DATA_TEMPLATE_FILE_PATH'),
            "consumer_pool_size": os.environ.get('CONSUMER_POOL_SIZE'),
            "sql_fetch_size": os.environ.get('SQL_FETCH_SIZE'),
            "delete_after_query": strtobool(os.environ.get('DELETE_AFTER_QUERY', 'False')),
            "delete_record_column": os.environ.get('DELETE_RECORD_COLUMN'),
            "delete_sql_file_path": os.environ.get('DELETE_SQL_FILE_PATH')
    }
  
    sql_file_path = """/home/user/your_sql_file.sql"""
    data_template_file_path = """/home/user/your_data_template_file.tpl""" 
    loop = asyncio.get_event_loop()
    try:
      loop.run_until_complete(
        perform_task(
          loop=loop,
          consumer_pool_size=10,
          sql_file_path=sql_file_path,
          config=config,
          consumer_pool_size=10, 
          sql_fetch_size=1000
        )
      )
    finally:
      loop.close()
```

This library uses [aio_pika](https://aio-pika.readthedocs.io/en/latest/), [aiopg](https://aiopg.readthedocs.io/en/stable/), [jinja2](https://jinja2docs.readthedocs.io/en/stable/) and [psycopg2](https://www.psycopg.org/docs//) packages.

### Standalone
You can also call this library as standalone job command.  Just set required environment variables and run `psql2rabbitmq`. This usecase perfectly fits when you need run it on cronjobs or kubernetes jobs. 

**Required environment variables:**
- MQ_HOST
- MQ_PORT (optional)
- MQ_VHOST
- MQ_USER
- MQ_PASS
- MQ_EXCHANGE
- MQ_ROUTING_KEY
- DB_HOST
- DB_PORT (optional)
- DB_USER
- DB_PASS
- DB_DATABASE
- SQL_FILE_PATH (File path contains select sql query. Ex: `/home/user/your_sql_file`)
- DATA_TEMPLATE_FILE_PATH (File path contains reqested data template. Ex: `/home/user/your_data_template_file`)
- CONSUMER_POOL_SIZE (optional, default value: 10)
- SQL_FETCH_SIZE (optional, default value: 1000)
- LOG_LEVEL (Logging level. See: [Python logging module docs](https://docs.python.org/3/library/logging.html#logging-levels))
- DELETE_AFTER_QUERY (Delete record after query mode. Optional, default value: False)
- DELETE_RECORD_COLUMN (Column name for value used by where condition. Optional, define when DELETE_AFTER_QUERY mode is active)
- DELETE_SQL_FILE_PATH (File path contains delete sql query. Optional, define when DELETE_AFTER_QUERY mode is active)

**Example Kubernetes job:** 
 You can see it to [kube.yaml](kube.yaml)