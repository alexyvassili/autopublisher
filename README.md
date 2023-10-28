# autopublisher
Script for automatic publish news and updates from email to drupal site

## MacOS installation

If you have `Pillow` installation error, you need 
to install `zlib` requirement for Pillow and add flags for compiler:

`$ brew install zlib`

`$ export LDFLAGS="-L/opt/homebrew/opt/zlib/lib"`

`$ export CPPFLAGS="-I/opt/homebrew/opt/zlib/include"`
