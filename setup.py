from setuptools import setup, find_packages

setup(
    name="camunda-external-task-client-python3",
    version="2.0.0",
    author="Alexander Neumann",
    author_email="aleneum@gmail.com",
    packages=find_packages(exclude=("tests",)),
    url="https://github.com/OpenAvikom/camunda-external-task-client-python3",
    license="LICENSE.txt",
    description="Camunda External Task Client for Python 3.8+",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    include_package_data=True,
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
    ],
)
