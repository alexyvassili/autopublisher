import os
import prepare
import publish


def current_directory():
    folder = os.getcwd()
    print('Prepare...')
    title, html, jpegs = prepare.news(folder)
    print('Publish...')
    publish.news(title, html, jpegs)


if __name__ == "__main__":
    current_directory()
