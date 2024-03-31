# -*- coding: utf-8 -*-
from os import path

from offregister_fab_utils.apt import apt_depends, is_installed
from offregister_fab_utils.ubuntu.systemd import restart_systemd
from patchwork.files import append, exists
from pkg_resources import resource_filename


def install0(c, *args, **kwargs):
    if len(is_installed(c, "odoo")) == 0:
        return "already installed odoo"

    if not exists(c, runner=c.run, path="/etc/apt/sources.list.d/odoo.list"):
        c.sudo("wget -O - https://nightly.odoo.com/odoo.key | apt-key add -")
        append(
            c,
            c.sudo,
            "/etc/apt/sources.list.d/odoo.list",
            "deb http://nightly.odoo.com/11.0/nightly/deb/ ./",
        )

    apt_depends(c, "postgresql", "odoo", "libldap2-dev", "libsasl2-dev")
    c.sudo("pip3 install pip==9.0.3")
    c.sudo("pip3 install vobject qrcode pyldap num2words")

    return "installed odoo"


def configure1(c, *args, **kwargs):
    server_name = kwargs.get("SERVER_NAME", kwargs.get("DNS_NAME"))
    if not server_name:
        raise TypeError("SERVER_NAME or DNS_NAME must be specified")

    upload_template_fmt(
        c,
        resource_filename(
            "offregister_odoo", path.join("conf", "nginx-sites-available.conf")
        ),
        "/etc/nginx/sites-enabled/odoo",
        use_sudo=True,
        backup=False,
        context={"SERVER_NAME": server_name},
    )

    return "configured odoo"


def restart_nginx2(c, *args, **kwargs):
    return restart_systemd("nginx")
