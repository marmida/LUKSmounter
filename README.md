LUKSMounter
===

LUKSMounter is a tiny GUI application that has a very narrow use case: it manages loopback devices and mounts LUKS crypto containers stored inside plain files.  This is different than the normal LUKS use case, which usually applies to whole filesystems and is tied into `/etc/crypttab`.

I wrote this because I am constantly forgetting to unmount my encrypted disks, leaving them available and readable when I don't need them to be.  Because this runs as a GUI app, your desktop manager should show it running, which hopefully is enough to remind you that you should close it before you scamper off for a week while your roommates try to snoop about your computer.

Installation
---

1. install `cryptsetup` via your package manager
1. download LUKSmounter and unpack it somewhere
1. copy the configuration file to `~/.luksmounter` and edit it
1. add the program to your GUI launcher.  I've included a sample application file for Unity.
