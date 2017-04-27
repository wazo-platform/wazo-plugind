# Integration tests

## Adding new git repos to the assets

To create a new git repo for a test, add a directory with a name ending with "-git" in the asset
and execute make create-git.

These repositories should not be commited.

To reference the created repos in your test or docker-compose use the same name and location without the "-git"

Example:

<asset>/tmp/malicious-repo-git
  - package.yml
  - package.sh
  - ...
  
will generate

<asset>/tmp/maliciout-repo
  - package.yml
  - package.sh
  - .git
  - ...
