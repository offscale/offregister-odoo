from os import path

from fabric.contrib.files import append, exists, upload_template
from fabric.operations import sudo

from offregister_fab_utils.apt import apt_depends, is_installed
from offregister_fab_utils.ubuntu.systemd import restart_systemd
from pkg_resources import resource_filename


def install0(*args, **kwargs):
    if len(is_installed("odoo")) == 0:
        return "already installed odoo"

    if not exists("/etc/apt/sources.list.d/odoo.list"):
        sudo("wget -O - https://nightly.odoo.com/odoo.key | apt-key add -")
        append(
            "/etc/apt/sources.list.d/odoo.list",
            "deb http://nightly.odoo.com/11.0/nightly/deb/ ./",
            use_sudo=True,
        )

    apt_depends("postgresql", "odoo", "libldap2-dev", "libsasl2-dev")
    sudo("pip3 install pip==9.0.3")
    sudo("pip3 install vobject qrcode pyldap num2words")

    return "installed odoo"


def configure1(*args, **kwargs):
    server_name = kwargs.get("SERVER_NAME", kwargs.get("DNS_NAME"))
    if not server_name:
        raise TypeError("SERVER_NAME or DNS_NAME must be specified")

    upload_template(
        resource_filename(
            "offregister_odoo", path.join("conf", "nginx-sites-available.conf")
        ),
        "/etc/nginx/sites-enabled/odoo",
        use_sudo=True,
        backup=False,
        context={"SERVER_NAME": server_name},
    )

    return "configured odoo"


def restart_nginx2(*args, **kwargs):
    return restart_systemd("nginx")
