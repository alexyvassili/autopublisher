"""
This is fabfile for install and update autopublisher on server
Use this file through `make` command
"""

from pathlib import Path

from fabric.api import get, put, run, sudo
from fabric.contrib.files import exists
from fabric.state import env


BASE_PACKAGES = [
    "apt-transport-https", "ca-certificates", "locales",
    "tzdata", "openssl",
]

BASE_APPS = [
    "curl", "mc", "procps",
    "vim", "wget",
]

PYTHON_PACKAGES = [
    "libpython3.11-stdlib", "python3-pip", "python3-poetry",
    "python3-xvfbwrapper", "python3.11-distutils", "python3.11-minimal",
    "python3.11-venv", "xvfb",
]

SYSTEM_APPS = [
    "firefox-esr", "firefox-esr-l10n-ru", "libmagic1",
    "libreoffice-writer",
]

IMAGEMAGICK_DEPENDENCIES = [
    "ghostscript", "hicolor-icon-theme", "libdjvulibre21",
    "libgs10", "libheif1", "libjxl0.9",
    "liblqr-1-0", "libopenexr-3-1-30", "libpangocairo-1.0-0",
    "libraqm0", "libraw-bin", "libraw23",
    "librsvg2-2", "librsvg2-bin", "libwebpdemux2",
    "libwebpmux3", "libwmflite-0.2-7", "libzip4",
    "netpbm",
]

IMAGEMAGICK_BUILD_DEPENDENCIES = [
    "bzip2", "cairosvg", "gir1.2-pangocairo-1.0-dev",
    "gsfonts-other", "libbzip3-dev", "libdjvulibre-dev",
    "libdjvulibre21", "libfontconfig-dev", "libfreetype-dev",
    "libfreetype6-dev", "libgif-dev", "libgs-dev",
    "libgvc6", "libheif-dev", "libjpeg-dev",
    "libjpeg62", "libjxl-dev", "libjxl-devtools",
    "liblcms2-dev", "liblqr-dev", "liblzma-dev",
    "libopenexr-dev", "libopenjp2-7-dev", "libpango1.0-dev",
    "libperl-dev", "libpng-dev", "libraqm-dev",
    "libraw-dev", "librsvg2-dev", "libtiff-dev",
    "libtiff5-dev", "libwebp-dev", "libwebpdemux2",
    "libwebpmux3", "libwmf-dev", "libxml2-dev",
    "libzip-dev", "libzstd-dev", "libzstd1",
    "pango1.0-tools", "wmf",
]


def set_env() -> None:
    env.GECKODRIVER_URL = (
        "https://github.com/mozilla/geckodriver/releases/"
        "download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz"
    )
    env.IMAGEMAGICK_URL = (
        "https://github.com/ImageMagick/ImageMagick/"
        "archive/refs/tags/7.1.1-27.tar.gz"
    )
    env.INSTALL_PATH = "/usr/local/share/autopublisher"
    env.VENV_PYTHON_PATH = f"{env.INSTALL_PATH}/bin/python3"
    env.BUILD_DIR = "/tmp/autopublisher_build"  # noqa:S108
    env.BUILD_APP_DIR = "/tmp/autopublisher"  # noqa:S108
    env.VENV_BUILD_DIR = f"{env.BUILD_APP_DIR}/env"
    env.VENV_BUILD_PYTHON_PATH = f"{env.VENV_BUILD_DIR}/bin/python3"


def bootstrap() -> None:
    set_env()
    check_deb()
    check_dist()
    setup_debian()
    install_python()
    install_system_apps()
    install_gecko_driver()
    install_imagemagick()
    create_app_user()
    install_app()
    set_service()
    restart_all()


def deploy() -> None:
    set_env()
    run("uname -a")
    check_dist()
    install_app()
    restart_all()


def check_deb() -> None:
    if not Path("deb/imagemagick-7-full-7.1.1-27.deb").exists():
        raise FileNotFoundError(
            "File not found: deb/imagemagick-7-full-7.1.1-27.deb"
            "Maybe you need to run `make build-magick` "
            "to build imagemagick package",
        )


def check_dist() -> None:
    if not Path("dist").exists():
        raise FileNotFoundError(
            "Directory `dist/` does not exists. "
            "Maybe you need to run `make build` to build app",
        )
    items = list(map(str, Path("dist").iterdir()))
    whls = [item for item in items if item.endswith(".whl")]
    if not whls:
        raise FileNotFoundError(
            "No .whl found in `dist/` directory. "
            "Maybe you need to run `make build` to build app",
        )
    if "requirements.txt" not in items:
        raise FileNotFoundError(
            "File `requirements.txt` was not found in `dist/` directory. "
            "Maybe you need to run `make build` to build app",
        )


def setup_debian() -> None:
    put(
        local_path="debian/config/sources.list",
        remote_path="/etc/apt/sources.list",
        use_sudo=True,
    )
    sudo("apt-get update && apt-get install -y aptitude")
    sudo("aptitude update && aptitude upgrade -y")
    sudo("aptitude install -y " + " ".join(BASE_PACKAGES))
    sudo("update-ca-certificates")
    run("export SSL_CERT_DIR='/etc/ssl/certs'")
    sudo("aptitude install -y " + " ".join(BASE_APPS))


def setup_build_system() -> None:
    setup_debian()
    sudo("aptitude install -y build-essential")


def install_python() -> None:
    sudo("aptitude install -y " + " ".join(PYTHON_PACKAGES))


def install_system_apps() -> None:
    sudo("aptitude install -y " + " ".join(SYSTEM_APPS))


def install_gecko_driver() -> None:
    run(f"wget {env.GECKODRIVER_URL} -O /tmp/geckodriver.tar.gz")
    _mkdir("/tmp/autopublisher_geckodriver")  # noqa:S108
    run("tar xvzf /tmp/geckodriver.tar.gz -C /tmp/autopublisher_geckodriver")
    sudo("cp /tmp/autopublisher_geckodriver/geckodriver /usr/local/bin")
    run("rm -fr /tmp/autopublisher_geckodriver")
    run("rm /tmp/geckodriver.tar.gz")


def install_imagemagick() -> None:
    sudo("aptitude install -y " + " ".join(IMAGEMAGICK_DEPENDENCIES))
    put(local_path="deb/imagemagick-7-full-7.1.1-27.deb", remote_path="/tmp/")  # noqa:S108
    sudo("dpkg -i /tmp/imagemagick-7-full-7.1.1-27.deb")


def create_app_user() -> None:
    # переписать имя пользователя как константу
    run("id -u alexey &>/dev/null || sudo useradd -g users alexey")
    sudo("mkdir -p /home/alexey")
    sudo("chown alexey /home/alexey")


def install_app() -> None:
    if not exists(env.VENV_PYTHON_PATH):
        sudo(f"mkdir -p {env.INSTALL_PATH}")
        sudo(f"chown alexey {env.INSTALL_PATH}")
        sudo(f"python3.11 -m venv {env.INSTALL_PATH}", user="alexey")
        sudo(
            f"{env.INSTALL_PATH}/bin/pip install -U pip setuptools wheel",
            user="alexey",
        )
    # TODO: переписать пути на константы
    run("rm -fr /tmp/dist")
    _mkdir("/tmp/dist")  # noqa:S108
    put(local_path="dist/*", remote_path="/tmp/dist/")  # noqa:S108
    sudo(
        f"{env.INSTALL_PATH}/bin/pip install -r /tmp/dist/requirements.txt",
        user="alexey",
    )
    sudo(
        f"{env.INSTALL_PATH}/bin/pip install /tmp/dist/*.whl",
        user="alexey",
    )
    sudo(
        f"find {env.INSTALL_PATH}/bin/ -name 'autopublisher*' "
        "-exec ln -snf '{}' /usr/local/bin/ ';'",
    )
    run("rm -fr /tmp/dist")


def set_service() -> None:
    put(
        local_path="fabdeploy/autopublisher.service",
        remote_path="/etc/systemd/system/",
        use_sudo=True,
    )
    sudo("systemctl enable autopublisher")


def stop_service() -> None:
    set_env()
    sudo("systemctl stop autopublisher")


def restart_service() -> None:
    set_env()
    restart_all()


def restart_all() -> None:
    sudo("systemctl restart autopublisher")


def clean_build() -> None:
    run(f"rm -fr {env.BUILD_DIR}")


def build_magick() -> None:
    set_env()
    clean_build()
    setup_build_system()
    _mkdir(env.BUILD_DIR)
    _mkdir(f"{env.BUILD_DIR}/imagemagick-7-full-7.1.1-27")
    sudo("aptitude install -y " + " ".join(IMAGEMAGICK_BUILD_DEPENDENCIES))
    run(
        f"cd {env.BUILD_DIR} && "
        f"wget {env.IMAGEMAGICK_URL} -O ImageMagick-7.1.1-27.tar.gz && "
        f"tar -xvzf ImageMagick-7.1.1-27.tar.gz",
    )
    run(
        f"cd {env.BUILD_DIR}/ImageMagick-7.1.1-27 && "
        f"./configure --disable-shared --disable-installed --disable-openmp "
        f'--prefix=\"{env.BUILD_DIR}/imagemagick-7-full-7.1.1-27/usr/local\" '
        f"--without-x --with-gslib --with-modules --with-bzlib -with-djvu "
        f"--with-dps --with-fontconfig --with-freetype --with-gslib "
        f"--with-gvc --with-heic --with-jbig --with-jpeg --with-jxl "
        f"--with-dmr --with-lcms --with-lqr --with-lzma "
        f"--with-magick-plus-plus --with-openexr --with-openjp2 "
        f"--with-pango --with-png --with-raqm --with-raw --with-rsvg "
        f"--with-tiff --with-webp --with-wmf --with-xml --with-zip "
        f"--with-zlib --with-zstd && "
        f"make && "
        f"make install",
    )
    put(
        local_path="debian/imagemagick/DEBIAN",
        remote_path=f"{env.BUILD_DIR}/imagemagick-7-full-7.1.1-27/",
    )
    run(f"dpkg-deb --build {env.BUILD_DIR}/imagemagick-7-full-7.1.1-27")
    get(
        remote_path=f"{env.BUILD_DIR}/imagemagick-7-full-7.1.1-27.deb",
        local_path="deb/",
    )
    clean_build()


def load_manifest() -> list[str]:
    with Path("MANIFEST.in").open() as f:
        items = [item.strip() for item in f.readlines()]
    return [item for item in items if item]


def _build_app() -> None:
    run(f"rm -fr {env.BUILD_APP_DIR}")
    _mkdir(env.BUILD_APP_DIR)
    for item in load_manifest():
        put(local_path=item, remote_path=f"{env.BUILD_APP_DIR}/")
    run(f"python3.11 -m venv {env.VENV_BUILD_DIR}")
    run(f"{env.VENV_BUILD_DIR}/bin/pip install -U pip setuptools wheel")
    run(
        f"cd {env.BUILD_APP_DIR} && "
        f"poetry env use {env.VENV_BUILD_PYTHON_PATH} && "
        f"poetry --version && "
        f"poetry env info && "
        f"poetry install && "
        f"poetry build -f wheel && "
        f"poetry export -f requirements.txt -o dist/requirements.txt",
    )
    get(remote_path=f"{env.BUILD_APP_DIR}/dist/*", local_path="dist/")
    run(f"rm -fr {env.BUILD_APP_DIR}")


def bootstrap_system_and_build_app() -> None:
    set_env()
    setup_build_system()
    install_python()
    _build_app()


def rebuild_app() -> None:
    set_env()
    _build_app()


def _mkdir(path: str, *, use_sudo: bool = False, chown: bool = False) -> None:
    if use_sudo:
        sudo(f"mkdir -p {path}")
        if chown:
            sudo(f"chown {env.USER} {path}")
    else:
        run(f"mkdir -p {path}")
