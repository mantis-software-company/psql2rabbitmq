import setuptools

setuptools.setup(
    name="psql2rabbitmq-as-json",
    version="0.0.0",
    author="Umit YILMAZ",
    author_email="info@mantis.com.tr",
    description="Asynchronous PostgreSQL data read and publish to RabbitMQ library",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    platforms="all",
    url="https://github.com/mantis-software-company/psql2rabbitmq-as-json",
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
    install_requires=['aiopg', 'aio_pika', 'jinja2', 'psycopg2'],
    python_requires=">3.6.*, <4",
    packages=['psql2rabbitmq_as_json'],
    scripts=['bin/psql2rabbitmq-as-json']
)

