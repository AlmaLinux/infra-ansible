# PINNWAND
=========

The aim of the role is to install [pinnwand](https://pinnwand.readthedocs.io/en/latest/) (a python pastebin webapp), alongside with mysql (as dbserver) and basic configuration for the pastebin app and a virtual host as reverse proxy. The webapp is run as an standard operating sytem user with a **/sbin/nologin** shell for security reason.

## Requirements
------------

Apache web server has to be previously installed on the target node

## Role Variables
--------------

Variables have been defined in the **vars/main.yml** and in **default/main.yml** In vars/main.yml there are:

In *vars/main.yml* there is the fqdn of pastebin website (used to configure the apache virtual host)

`pinnwand_fqdn: pinnwand.local`

In *default/main.yml* there are:

Operating system user variables
```
pinnwand_os_user: pinnwand
pinnwand_home_dir: /opt
```
pinnwand webapp configuration
```
pinwwnad_http_port: 8000
pinnwand_cfg_file: pinnwand.toml
```

pinnwand database configuration parameters
```
dbserver: mysql-server
dbclient: mysql
dbserver_service: mysqld
pinnwand_db_name: pinnwand_db
pinnwand_db_user: pinnwand
pinnwand_db_pass: pinnwand
pinnwand_db_driver: mysql+pymysql
pinnwand_db_host: 127.0.0.1
```

## Dependencies
------------

None

## Example Playbook
----------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:
```
---
- hosts: mantis
  become: yes

  tasks:
    - name: pinnwand role
      ansible.builtin.include_role:
        name: pinnwand
...
```

License
-------

BSD

Author Information
------------------

Luca Ceccarani
