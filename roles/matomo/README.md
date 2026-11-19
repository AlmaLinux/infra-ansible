MATOMO
=============================

This role is a fork from Consensus Enterprises' Matomo role and has been adequate for RedHat based os.
T

Overview
--------

TO BE UPDATED

Requirements
------------

* A RedHat OS (e.g. Almalinux, Rocky)
* The Nginx Web server
* MySQL (version 5.5 or greater) or MariaDB

TO BE UPDATED

Role Variables
--------------
TO BE UPDATED

Dependencies
------------

### geerlingguy.certbot

[geerlingguy/certbot](https://galaxy.ansible.com/geerlingguy/certbot) is used for the HTTPS certificate management, installation and renewals.

See the [default variables used](https://gitlab.com/consensus.enterprises/ansible-roles/ansible-role-matomo/blob/master/tasks/get-https-certificate.yml) when calling it.

geerlingguy.repo-epel

Example Playbook
----------------

TO BE UPDATED

```yaml
- hosts: servers
  become: true
  roles:
    - ansible-role-matomo
  vars:
    # https://github.com/ansible/ansible/issues/45852
    # https://www.toptechskills.com/ansible-tutorials-courses/how-to-fix-usr-bin-python-not-found-error-tutorial/
    ansible_python_interpreter: /usr/bin/python3
    # Main role variable settings.
    matomo_domain: matomo.example.com
    matomo_https_certificate_admin_email: tech@example.com
    matomo_superuser_password: YOUR_SUPER_SECRET_ADMIN_PASSWORD_FOR_THE_WEB_UI
```

Testing
-------

Tests can be run like so (with more or fewer "v"s for verbosity):

```sh
ansible-playbook -vv --ask-become-pass --inventory TARGET_HOSTNAME, /path/to/this/role/tests/TEST_NAME.yml
```

Feel free to add your own tests in `tests/`, using existing ones as examples.  Contributions welcome.

Issue Tracking
--------------

For bugs, feature requests, etc., please visit the [issue tracker](https://gitlab.com/consensus.enterprises/ansible-roles/ansible-role-matomo/-/boards).

License
-------

GNU AGPLv3

Author Information
------------------

Written by me Luca Ceccarani based on Consensus work
