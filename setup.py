import setuptools

setuptools.setup(
    name="psql2rabbitmq",
    version="1.0.6.4",
    author="Umit YILMAZ",
    author_email="umutyilmaz44@gmail.com",
    description="Asynchronous PostgreSQL data read and publish to RabbitMQ library",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    platforms="all",
    url="https://github.com/mantis-software-company/psql2rabbitmq",
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Internet",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Testing",
        "Intended Audience :: Developers",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Operating System :: Microsoft",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8"
    ],
    install_requires=['aiopg', 'aio_pika', 'jinja2', 'psycopg2-binary'],
    python_requires=">3.6.*, <4",
    packages=['psql2rabbitmq'],
    scripts=['bin/psql2rabbitmq']
)
