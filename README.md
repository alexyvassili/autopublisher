# autopublisher
Script for automatic publish news and updates from email to drupal site

## MacOS installation

### Required packages and applications

1. Install LibreOffice: 
https://ru.libreoffice.org


2. Download and unpack Gecko driver for Selenium: 
https://github.com/mozilla/geckodriver/releases


3. Copy `geckodriver` to $PATH directory, for example to `/usr/local/bin`


4. Install ImageMagick: `brew install imagemagick`

---

If you have `Pillow` installation error (from `requirements.txt`), you need 
to install `zlib` requirement for Pillow and add flags for compiler:

`$ brew install zlib`

`$ export LDFLAGS="-L/opt/homebrew/opt/zlib/lib"`

`$ export CPPFLAGS="-I/opt/homebrew/opt/zlib/include"`
