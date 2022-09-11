from os import path
from random import randint

from fabric.operations import prompt
from offregister_fab_utils.apt import apt_depends, get_pretty_name
from offutils import gen_random_str
from patchwork.files import append
from pkg_resources import resource_filename

from offregister_odoo import __author__


def install_docker0(*args, **kwargs):
    dist = get_pretty_name()
    if not dist == "precise":
        raise NotImplementedError("Remote OS is not {}".format(dist))

    apt_depends(c, "apt-transport-https", "ca-certificates")
    c.sudo(
        "apt-key adv --keyserver hkp://ha.pool.sks-keyservers.net:80 "
        "--recv-keys 58118E89F3A912897C070ADBF76221572C52609D"
    )
    append(
        c,
        c.sudo,
        "/etc/apt/sources.list.d/docker.list",
        "deb https://apt.dockerproject.org/repo ubuntu-{dist} main".format(dist=dist),
    )

    docker_running = c.run("status docker", hide=True, warn=True).exited == 0
    if not docker_running and dist == "precise":
        apt_depends(c, "linux-image-generic-lts-trusty")
        if (lambda reboot: reboot.lower() in frozenset(("y", "yes")))(
            prompt("Reboot? [y|n]")
        ):
            c.sudo("reboot")
        apt_depends(c, "docker-engine")  # Reboot for this

        # Preferably never reach these two lines
        c.sudo("service docker start")
        c.sudo("docker run hello-world")

    if c.run("grep -q docker /etc/group", hide=True, warn=True).exited != 0:
        c.sudo("groupadd docker")
        c.sudo("usermod -aG docker $USER")
        c.sudo("docker run hello-world")


def _destroy_docker_container(name, destroy=None):
    container_id = c.run(
        'docker ps -a --format "{{.ID}}" -f' + "name={name}".format(name=name)
    )
    if len(container_id) > 15:
        raise NotImplementedError("Support for multiple containers of same name")

    if container_id:
        c.run("docker stop {container_id}".format(container_id=container_id))
        if (
            destroy is False
            or destroy is None
            and not (lambda reboot: reboot.lower() in frozenset(("y", "yes")))(
                prompt("Destroy {name}? [y|n]".format(name=name))
            )
        ):
            return "Did not destroy {name}.".format(name=name)

        return c.run(
            "docker rm --force {container_id}".format(container_id=container_id)
        )


def setup_postgres1(*args, **kwargs):
    _destroy_docker_container("odoo", destroy=True)
    _destroy_docker_container("db", destroy=True)
    c.run(
        "docker run -d -e POSTGRES_USER={user} -e POSTGRES_PASSWORD={password} --name db postgres:9.4".format(
            user=gen_random_str(randint(10, 20)),
            password=gen_random_str(randint(10, 20)),
        )
    )


def setup_odoo2(*args, **kwargs):
    c.sudo("stop teamcity && rm -rf /etc/init/teamcity.conf", hide=True, warn=True)
    _destroy_docker_container("odoo", destroy=True)
    for fname in ("stdout", "stderr"):
        c.sudo("touch /var/log/upstart/odoo.{fname}.log".format(fname=fname))
        c.sudo(
            "chown $USER:$GROUP /var/log/upstart/odoo.{fname}.log".format(fname=fname)
        )
    upload_template_fmt(
        c,
        resource_filename("offregister_odoo", path.join("conf", "odoo.conf")),
        "/etc/init/odoo.conf",
        use_sudo=True,
        context={"USER": c.run("echo $USER").stdout.rstrip(), "AUTHOR": __author__},
    )
    if c.run("status odoo", hide=True, warn=True).exited != 0:
        c.sudo("start odoo")
