"""
    This is fabfile for deploying autopublisher on debian stretch on custom python 3.6.5
"""
import os
import sys

from fabric.state import env
from fabric.api import cd, run, sudo, settings
from fabric.contrib.files import exists, upload_template

from secrets import DEPLOY_HOST, DEPLOY_USER
from prepare import SOFFICE_PATH


env.hosts = [f'{DEPLOY_USER}@{DEPLOY_HOST}']


def bootstrap():
    # input('setenv')
    set_env()
    run('uname -a')
    # input('prepare package system')
    prepare_package_system()
    # input('prepare_interpreter')
    install_pydevel_packages()
    prepare_interpreter()
    # input('install_system_libs')
    install_system_libs()
    # input('install_Libreoffice')
    install_libreoffice()
    # input('create_folders')
    create_folders()
    # input('get_src')
    get_src()
    # input('set_secrets')
    set_secrets()
    # input('create_virtualenv')
    create_virtualenv()
    # input('install_venv_libs')
    install_venv_libs()
    # input('download gecko driver')
    download_gecko_driver()
    # input('set_service')
    set_service()
    # input('restart_all')
    restart_all()


def deploy():
    set_env()
    run('uname -a')
    get_src()
    set_secrets()
    install_venv_libs()
    restart_all()


def set_env():
    env.USER = DEPLOY_USER
    env.BASE_PATH = f'/home/{env.USER}/projects'
    env.VENV_PATH = f'/home/{env.USER}/.pyenv/versions'
    env.PROJECT_NAME = 'autopublisher'
    env.REMOTE_PROJECT_PATH = os.path.join(env.BASE_PATH, env.PROJECT_NAME)
    env.REMOTE_VENV_PATH = os.path.join(env.VENV_PATH,
                                        env.PROJECT_NAME)
    env.GIT_REPO_PATH = "https://github.com/alexyvassili/autopublisher.git"
    env.PYTHON_VESRION = "3.6.5"
    env.PYENV_PATH = f'/home/{env.USER}/.pyenv'
    env.BASE_REMOTE_NTERPRETER = f'/home/{env.USER}/.pyenv/versions/{env.PYTHON_VESRION}/bin/python'
    env.REMOTE_VENV_PATH = f'/home/{env.USER}/.pyenv/versions/{env.PROJECT_NAME}'
    env.VENV_REMOTE_PYTHON_PATH = f'/home/{env.USER}/.pyenv/versions/{env.PROJECT_NAME}/bin/python'


def prepare_package_system():
    if not exists('/etc/apt/sources.list.old'):
        sudo('mv /etc/apt/sources.list /etc/apt/sources.list.old')
        upload_template('deploy/sources.list', '/etc/apt/', use_sudo=True)
    sudo('apt-get update && apt-get upgrade -y')
    sudo('apt-get install -y aptitude')


def install_pydevel_packages():
    # Libraries for loading and installing Python
    sudo('aptitude install -y git curl mc vim net-tools gcc build-essential '
         'python-dev libreadline-dev libbz2-dev libssl-dev libsqlite3-dev libxslt1-dev libxml2-dev zlib1g zlib1g-dev')


def prepare_interpreter():
    if not exists(env.PYENV_PATH):
        print('Pyenv not found, loading...')
        run("curl -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash")

    if not exists(env.BASE_REMOTE_NTERPRETER):
        print(f'Interpreter not found, load Python {env.PYTHON_VESRION}')
        run(f"{env.PYENV_PATH}/bin/pyenv install {env.PYTHON_VESRION}")


def install_system_libs():
    sudo('aptitude install -y imagemagick git xvfb x11-utils firefox-esr default-jre')


def install_libreoffice():
    if not exists(SOFFICE_PATH):
        run('wget http://download.documentfoundation.org/libreoffice/stable/6.2.4/deb/x86_64/LibreOffice_6.2.4_Linux_x86-64_deb.tar.gz -O /tmp/libreoffice.tar.gz')
        run('mkdir /tmp/libreoffice_setup')
        # распаковываем все файлы без сохранения структуры директорий
        run('tar xvzf /tmp/libreoffice.tar.gz -C /tmp/libreoffice_setup/ --strip-components 2')
        sudo('dpkg -i /tmp/libreoffice_setup/*.deb')
        run('rm /tmp/libreoffice_setup/*')
        run('rmdir /tmp/libreoffice_setup')
        run('rm /tmp/libreoffice.tar.gz')


def create_folders():
    _mkdir(env.REMOTE_PROJECT_PATH, use_sudo=True, chown=True)
    _mkdir(env.REMOTE_VENV_PATH, use_sudo=True, chown=True)


def get_src():
    if not exists(os.path.join(env.REMOTE_PROJECT_PATH, '.git')):
        run(f'git clone {env.GIT_REPO_PATH} {env.REMOTE_PROJECT_PATH}')
    else:
        run(f'cd {env.REMOTE_PROJECT_PATH}; git pull')


def set_secrets():
    # upload_template(
    #     os.path.join(env.PROJECT_NAME, 'secrets.py'),
    #     os.path.join(env.REMOTE_PROJECT_PATH, env.PROJECT_NAME)
    # )
    upload_template('secrets.py', env.REMOTE_PROJECT_PATH)


def create_virtualenv():
    if not exists(env.VENV_REMOTE_PYTHON_PATH):
        run(f"{env.PYENV_PATH}/bin/pyenv virtualenv {env.PYTHON_VESRION} {env.PROJECT_NAME}")
        pip = os.path.join(env.REMOTE_VENV_PATH, 'bin', 'pip3')
        run(f'{pip} install --upgrade pip')


def install_venv_libs():
    requirements_txt = os.path.join(env.REMOTE_PROJECT_PATH, 'requirements.txt')
    run(f'{env.VENV_REMOTE_PYTHON_PATH} -m pip install -r {requirements_txt}')


def download_gecko_driver():
    if not exists('/usr/bin/geckodriver'):
        run('wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz -O /tmp/geckodriver.tar.gz')
        run('mkdir -p /tmp/geckodriver')
        run('tar xvzf /tmp/geckodriver.tar.gz -C /tmp/geckodriver')
        sudo('cp /tmp/geckodriver/geckodriver /usr/bin')
        run('rm /tmp/geckodriver/*')
        run('rmdir /tmp/geckodriver')
        run('rm /tmp/geckodriver.tar.gz')


def set_service():
    sudo('cp /var/www/autopublisher/fabdeploy/telegrambot.service /etc/systemd/system/')
    sudo('systemctl enable telegrambot')


def restart_all():
    sudo('systemctl restart telegrambot')


def _mkdir(path: str, use_sudo=False, chown=False):
    if use_sudo:
        sudo(f'mkdir -p {path}')
        if chown:
            sudo(f'chown {env.USER} {path}')
    else:
        run('mkdir -p %s' % path)


def _put_template(template_name, remote_path, use_sudo=False):
    upload_template(
        os.path.join('fabdeploy', template_name),
        remote_path,
        context={
            'app_name': env.PROJECT_NAME,
        },
        use_sudo=use_sudo,
    )
