# MANTISBT
=========

The aim of the role is to install mantisbt issue tracker, alongside with apache (as websever) and mysql (as dbserver).

## Requirements
------------
Put Selinux in **Permissive** mode otherwise the **url_get** method invoked by the admin/install.php page will not work. 
This is not the proper way to tackle the issue but it was he quickest one at least for me, the proper way is to properly configure selinux to allow the **url_get** method.

## Role Variables
--------------
Variables have been defined in the **vars/main.yml** and in **default/main.yml**
In *vars/main.yml* there are:

```
mantisbt_version: 2.27.0 #The version of mantis to be downloaded and installed
force_mnatisbt_installation: false #An hook to froce mantisbt installation independently if alaready installed
```

In *default/main.yml* there are:

Web server variables
```
webserver: httpd #Web server to be used
webserver_rootdoc: /var/www/html
#Used by firewalld rule
web_services:
  - http
  - https
```

DB server variables (type of db, username, password and dbname used during the mantisbt installation)
```
dbserver: mysql-server
dbclient: mysql
dbserver_service: mysqld
mantisbt_db_type: mysqli
mantisbt_db_name: bugtracker #This is the default database name suggested by the installation wizard
mantisbt_db_user: mantisbt
mantisbt_db_pass: mantisbt
```
Mantisbt download variables:
```
mantisbt_src_base_url: https://sourceforge.net/projects/mantisbt/files/mantis-stable
manstisbt_src_extension: tar.gz
mantisbt_pkg_name: 'mantisbt-{{ mantisbt_version }}.{{ manstisbt_src_extension }}' #mantisbt-2.27.0.tar.gz
mantisbt_digest_name: '{{ mantisbt_pkg_name }}.digests' #mantisbt-2.27.0.tar.gz.digests
mantisbt_tarball_local_dir: /opt`
```

Dependencies
------------

None

Example Playbook
----------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:
```
---
- hosts: mantis
  become: yes

  tasks:
    - name: mantis role
      ansible.builtin.include_role:
        name: mantisbt
...
```
License
-------

BSD

Author Information
------------------

Luca Ceccarani
