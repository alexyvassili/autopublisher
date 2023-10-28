"""
    This is fabfile for deploying autopublisher
    on debian stretch on custom preinstalled pyenv python
"""
import os

from fabric.state import env
from fabric.api import run, sudo
from fabric.contrib.files import exists, upload_template

from autopublisher.secrets import DEPLOY_HOST, DEPLOY_USER
from autopublisher.publish.prepare import SOFFICE_PATH


env.hosts = [f'{DEPLOY_USER}@{DEPLOY_HOST}']


def bootstrap():
    set_env()
    run('uname -a')
    prepare_interpreter()
    install_system_libs()
    install_libreoffice()
    create_folders()
    get_src()
    set_secrets()
    input()
    create_virtualenv()
    input()
    install_venv_libs()
    input()
    download_gecko_driver()
    input()
    install()
    input()
    set_service()
    input()
    restart_all()


def deploy():
    set_env()
    run('uname -a')
    get_src()
    set_secrets()
    install_venv_libs()
    install()
    restart_all()


def set_env():
    env.USER = DEPLOY_USER
    env.BASE_PATH = f'/home/{env.USER}/projects'
    env.VENV_PATH = f'/home/{env.USER}/.pyenv/versions'
    env.PROJECT_NAME = 'autopublisher'
    env.REMOTE_PROJECT_PATH = os.path.join(env.BASE_PATH, env.PROJECT_NAME)
    env.SECRETS_REMOTE_PATH = os.path.join(env.BASE_PATH, env.PROJECT_NAME, env.PROJECT_NAME)
    env.REMOTE_VENV_PATH = os.path.join(env.VENV_PATH,
                                        env.PROJECT_NAME)
    env.GIT_REPO_PATH = "https://github.com/alexyvassili/autopublisher.git"
    env.PYTHON_VERSION = "3.7.5"
    env.PYENV_PATH = f'/home/{env.USER}/.pyenv'
    env.BASE_REMOTE_NTERPRETER = f'/home/{env.USER}/.pyenv/versions/{env.PYTHON_VERSION}/bin/python'
    env.REMOTE_VENV_PATH = f'/home/{env.USER}/.pyenv/versions/{env.PROJECT_NAME}'
    env.VENV_REMOTE_PYTHON_PATH = f'/home/{env.USER}/.pyenv/versions/{env.PROJECT_NAME}/bin/python'


def prepare_interpreter():
    if not exists(env.PYENV_PATH):
        print('Pyenv not found, loading...')
        run("curl -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash")

    if not exists(env.BASE_REMOTE_NTERPRETER):
        print(f'Interpreter not found, load Python {env.PYTHON_VERSION}')
        run(f"{env.PYENV_PATH}/bin/pyenv install {env.PYTHON_VERSION}")


def install_system_libs():
    sudo('aptitude install -y imagemagick git xvfb x11-utils firefox-esr default-jre libmagic1 unrar')


def install_libreoffice():
    if not exists(SOFFICE_PATH):
        run('wget http://download.documentfoundation.org/libreoffice/stable/6.3.3/deb/x86_64/LibreOffice_6.3.3_Linux_x86-64_deb.tar.gz -O /tmp/libreoffice.tar.gz')
        run('mkdir /tmp/libreoffice_setup')
        # распаковываем все файлы без сохранения структуры директорий
        run('tar xvzf /tmp/libreoffice.tar.gz -C /tmp/libreoffice_setup/ --strip-components 2')
        sudo('dpkg -i /tmp/libreoffice_setup/*.deb')
        run('rm /tmp/libreoffice_setup/*')
        run('rmdir /tmp/libreoffice_setup')
        run('rm /tmp/libreoffice.tar.gz')


def create_folders():
    _mkdir(env.REMOTE_PROJECT_PATH, use_sudo=True, chown=True)
    # _mkdir(env.REMOTE_VENV_PATH, use_sudo=True, chown=True)


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
    upload_template('autopublisher/secrets.py', env.SECRETS_REMOTE_PATH)


def create_virtualenv():
    if not exists(env.VENV_REMOTE_PYTHON_PATH):
        run(f"{env.PYENV_PATH}/bin/pyenv virtualenv {env.PYTHON_VERSION} {env.PROJECT_NAME}")
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


def install():
    run(f'cd {env.REMOTE_PROJECT_PATH} && make sdist && {env.VENV_REMOTE_PYTHON_PATH} -m pip install dist/{env.PROJECT_NAME}*')


def set_service():
    sudo(f'cp {env.REMOTE_PROJECT_PATH}/fabdeploy/telegrambot.service /etc/systemd/system/')
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
