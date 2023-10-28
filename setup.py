import os
from importlib.machinery import SourceFileLoader

from pkg_resources import parse_requirements
from setuptools import find_packages, setup


module_name = "autopublisher"

module = SourceFileLoader(
    module_name, os.path.join(module_name, "__init__.py"),
).load_module()


def load_requirements(fname) -> list:
    requirements = []
    with open(fname) as fp:
        for req in parse_requirements(fp.read()):
            name = req.name
            if req.extras:
                name += "[" + ",".join(req.extras) + "]"
            requirements.append("{}{}".format(name, req.specifier))
    return requirements


setup(
    name=module_name.replace("_", "-"),
    version=module.__version__,
    author=module.__author__,
    author_email=module.authors_email,
    license=module.__license__,
    description=module.package_info,
    long_description="Script for automatic publish news and "
                     "updates from email to drupal site",
    platforms="all",
    classifiers=[
        "Intended Audience :: Developers",
        "Natural Language :: Russian",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    python_requires=">=3.8",
    packages=find_packages(exclude=["tests"]),
    install_requires=load_requirements("requirements.txt"),
    extras_require={"develop": load_requirements("requirements.dev.txt")},
    entry_points={
        "console_scripts": ["{0} = {0}.__main__:main".format(module_name)],
    },
)
