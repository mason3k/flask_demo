[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=for-the-badge)](https://github.com/pre-commit/precommit)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?&style=for-the-badge)](https://pycqa.github.io/isort/)
![GitHub last commit](https://img.shields.io/github/last-commit/mason3k/scripts?style=for-the-badge)
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg?style=for-the-badge)](https://github.com/PyCQA/bandit)

# Language Detector

A simple Flask application for detecting the most likely language for a snippet of text. It can be run completely offline or alternatively, it can reference an API.

Check it out: http://sujones.pythonanywhere.com/

## Test User

As an exercise, I implemented authentication for the site so that user's responses could be saved and retrieved. If you'd like to explore the site without registering, you can use the dummy bootstrapped user:

Username: `test@me.com` 
Password: `password`

## Developing

To run the app locally, run:

```shell
flask --app program run --debug
```
