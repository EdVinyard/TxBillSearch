mkdir -p dist-archive
mv dist/* dist-archive
python3 setup.py sdist bdist_wheel
