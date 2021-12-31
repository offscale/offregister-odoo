from os import path
from random import randint

from fabric.contrib.files import append, upload_template
from fabric.operations import prompt, run, sudo
from offregister_fab_utils.apt import apt_depends, get_pretty_name
from offutils import gen_random_str
from pkg_resources import resource_filename

from offregister_odoo import __author__


def install_docker0(*args, **kwargs):
    dist = get_pretty_name()
    if not dist == "precise":
        raise NotImplementedError("Remote OS is not {}".format(dist))

    apt_depends("apt-transport-https", "ca-certificates")
    sudo(
        "apt-key adv --keyserver hkp://ha.pool.sks-keyservers.net:80 "
        "--recv-keys 58118E89F3A912897C070ADBF76221572C52609D"
    )
    append(
        "/etc/apt/sources.list.d/docker.list",
        "deb https://apt.dockerproject.org/repo ubuntu-{dist} main".format(dist=dist),
        use_sudo=True,
    )

    docker_running = run("status docker", quiet=True, warn_only=True).succeeded
    if not docker_running and dist == "precise":
        apt_depends("linux-image-generic-lts-trusty")
        if (lambda reboot: reboot.lower() in frozenset(("y", "yes")))(
            prompt("Reboot? [y|n]")
        ):
            sudo("reboot")
        apt_depends("docker-engine")  # Reboot for this

        # Preferably never reach these two lines
        sudo("service docker start")
        sudo("docker run hello-world")

    if run("grep -q docker /etc/group", quiet=True, warn_only=True).failed:
        sudo("groupadd docker")
        sudo("usermod -aG docker $USER")
        sudo("docker run hello-world")


def _destroy_docker_container(name, destroy=None):
    container_id = run(
        'docker ps -a --format "{{.ID}}" -f' + "name={name}".format(name=name)
    )
    if len(container_id) > 15:
        raise NotImplementedError("Support for multiple containers of same name")

    if container_id:
        run("docker stop {container_id}".format(container_id=container_id))
        if (
            destroy is False
            or destroy is None
            and not (lambda reboot: reboot.lower() in frozenset(("y", "yes")))(
                prompt("Destroy {name}? [y|n]".format(name=name))
            )
        ):
            return "Did not destroy {name}.".format(name=name)

        return run("docker rm --force {container_id}".format(container_id=container_id))


def setup_postgres1(*args, **kwargs):
    _destroy_docker_container("odoo", destroy=True)
    _destroy_docker_container("db", destroy=True)
    run(
        "docker run -d -e POSTGRES_USER={user} -e POSTGRES_PASSWORD={password} --name db postgres:9.4".format(
            user=gen_random_str(randint(10, 20)),
            password=gen_random_str(randint(10, 20)),
        )
    )


def setup_odoo2(*args, **kwargs):
    sudo("stop teamcity && rm -rf /etc/init/teamcity.conf", quiet=True, warn_only=True)
    _destroy_docker_container("odoo", destroy=True)
    for fname in ("stdout", "stderr"):
        sudo("touch /var/log/upstart/odoo.{fname}.log".format(fname=fname))
        sudo("chown $USER:$GROUP /var/log/upstart/odoo.{fname}.log".format(fname=fname))
    upload_template(
        resource_filename("offregister_odoo", path.join("conf", "odoo.conf")),
        "/etc/init/odoo.conf",
        use_sudo=True,
        context={"USER": run("echo $USER"), "AUTHOR": __author__},
    )
    if run("status odoo", quiet=True, warn_only=True).failed:
        sudo("start odoo")
