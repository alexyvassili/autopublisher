try:
    from .version import __version__, version_info
except ImportError:
    version_info = (0, 0, 0)
    __version__ = "{}.{}.{}".format(*version_info)


authors = (("Alexey Vasilev", "escantor@gmail.com"),)
authors_email = ", ".join(email for _, email in authors)

__license__ = "MIT License"
__author__ = ", ".join(f"{name} <{email}>" for name, email in authors)

package_info = "Script for automatic publish news and updates " \
               "from email to drupal site"

# It's same persons right now
__maintainer__ = __author__


__all__ = (
    "__author__",
    "__author__",
    "__license__",
    "__maintainer__",
    "__version__",
    "version_info",
    "authors_email",
)
