# NOGGIN
=========

The aim of the role is to install [noggin](https://github.com/fedora-infra/noggin) on Redhat (ansible_os_family) based operating systems.
The installation of noggin is performed via rpm command and not dnf module because there's an [issue](https://bugzilla.redhat.com/show_bug.cgi?id=2277356) with the noggin package released on epel repository. Therefore the installation is performed this way:
- dnf module is used in downloadonly mode
- downloaded rpms are installed rpm *rpm --force
- downloaded rpms are removed

The role installs even the private key and public selfsigned cert used by nginx to be used in https.

## Requirements
------------

Put Selinux in **Permissive** mode otherwise the noggin application will not interact with freeipa servers. 
This is not the proper way to tackle the issue but it was he quickest one at least for me.

## Role Variables
--------------

Variables have been defined in the **vars/main.yml** and in **default/main.yml**
In *vars/main.yml* there are:
The name of the role to be included for RedHat based systems (Rocky, Alma)

```
repo_epel_role_name: geerlingguy.repo-epel
```

In *defaults/main.yml* there are:

Web server variables needed for installation and basic customization

```
webserver: nginx
webserver_rootdoc: /var/www/html
#Used by firewalld rule
web_services:
  - http
  - https
```
Noggin variables for installation

```
apply_noggin_install_workaround: True
noggin_temp_rpm_dir: /opt/noggin_rpms #This directory will be used to temporary download the rpms needed by noggin and manually installed because of a clash between nginx and noggin rpms
```
Noggin variables for web app configuration

```
#Variables used for noggin web app configuration
freeipa_admin_user: adminuser
freeipa_admin_pass: changeme
freeipa_hosts:
 - host: freeipa1.atm.local
   port: 443
 - host: freeipa2.atm.local
   port: 443
freeipa_cert_dir: /etc/ipa
freeipa_ca_cert_file: ipa_ca    .crt
```

[Flask-mail](https://flask-mail.readthedocs.io/en/latest/) variables used by noggin

```
noggin_mail_suppress_send: False
noggin_mail_server: smtp.gmail.com
noggin_mail_port: 587
noggin_use_tls: True
noggin_use_ssl: False
noggin_mail_username: myservice@email.com
noggin_mail_password: myserviceemailpassword
noggin_mail_default_sender: myservice@email.com
noggin_mail_debug: True
noggin_debug: True
```

#Variables user for noggin nginx configuration

```
ngnix_noggin_server_name: noggin.lab.local

nginx_noggin_enable_tls: True

noggin_private_key_dir: /etc/noggin/private-key
noggin_private_key_name: noggin-selfsigned.key
noggin_cert_dir: /etc/noggin/
noggin_cert_name: noggin-selfsigned.crt
```

Dependencies
------------
The **[geerlingguy.repo-epel](https://github.com/geerlingguy/ansible-role-repo-epel)** is used to enable the epel-repositories.

Example Playbook
----------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

```
- hosts: mantis
  become: yes

  tasks:
    - name: noggin role
      ansible.builtin.include_role:
        name: noggin
```

In order to override your sensitive data like:

- freeipa_admin_user
- freeipa_admin_pass
- noggin_mail_username
- noggin_mail_password
- noggin_mail_default_sender

Write a file (e.g. **nogginsecrevar.yml**) containing the variables with the proper values 

```
freeipa_admin_user: myipaadminuser
freeipa_admin_pass: myipadminpass
noggin_mail_username: mysecretmail@mail.com
noggin_mail_password: mysecretmailpass
noggin_mail_default_sender: mysecretmail@mail.com
```
then execute following command

`ansible-playbook noggin.yml -e @nogginsecrevar.yml`

License
-------

BSD

Author Information
------------------

Luca Ceccarani
