'''
Manage LUKS volume mounts in a GUI, so you don't forget to lock them when
they're no longer in use (because it has a Unity launcher entry still active).

Should be launched with elevated privs / gksudo.
'''

# setup pygtk for version selecting
import pygtk
pygtk.require('2.0')

import ConfigParser
import gtk
import os.path
import subprocess

def get_loopback_device(filename):
    '''
    Return the path to the loopback device for *filename*, or None if it's
    not yet created.
    '''
    losetup_out = subprocess.check_output(['losetup', '-j', filename])
    if not losetup_out:
        return None

    # the part before the first colon is the device name, e.g. /dev/loop0
    return losetup_out[:losetup_out.index(':')]

# based on http://ardoris.wordpress.com/2008/07/05/pygtk-text-entry-dialog/
def response_to_dialog(entry, dialog, response):
    'Implementation detail of prompt_passphrase, below'
    dialog.response(response)

def prompt_passphrase():
    '''
    Display a dialog asking the user for their passphrase.
    Returns the passphrase text, or None if the user canceled the dialog.
    '''
    #base this on a message dialog
    dialog = gtk.MessageDialog(
        None,
        gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
        gtk.MESSAGE_QUESTION,
        gtk.BUTTONS_OK_CANCEL,
    )

    # connect cancel button
    dialog.get_action_area().get_children()[1].connect('clicked',
        response_to_dialog, dialog, gtk.RESPONSE_CANCEL)

    dialog.set_markup('LUKS volume passphrase:')

    # create the text input field
    entry = gtk.Entry()
    entry.set_visibility(False)
    # allow the user to press enter to do ok
    entry.connect('activate', response_to_dialog, dialog, gtk.RESPONSE_OK)

    # add the entry field
    dialog.get_content_area().add(entry)
    dialog.show_all()

    # display the dialog - currently not modal
    response = dialog.run()
    ret = entry.get_text() if response == gtk.RESPONSE_OK else None
    dialog.destroy()
    return ret

class MounterWindow(gtk.Window):
    def __init__(self, config):
        super(MounterWindow, self).__init__(gtk.WINDOW_TOPLEVEL)

        # copy some values out of the config
        self.loopback_file = config.get('default', 'loopback_file')
        self.luks_device_name = config.get('default', 'luks_device_name')
        self.mount_point = config.get('default', 'mount_point')

        self.set_title('LUKSmounter')
        self.connect('destroy', self.shutdown)
        self.set_border_width(10)

        self.loop_dev = get_loopback_device(self.loopback_file)

        # add a vertical container
        self.box = gtk.VBox(False, spacing=0) # homogenous: all children are the same size
        self.add(self.box)

        # update labels and buttons
        self.refresh()
        self.show_all()
        self.show()

    def refresh(self):
        '''
        Update widgets to reflect current mount status.

        If *force* is True, then we always update, even 
        '''
        # wipe out existing controls
        for child in self.box.get_children():
            self.box.remove(child)

        # add some labels
        if self.loop_dev:
            label1 = gtk.Label("Loopback device: %s" % self.loop_dev)
            self.box.add(label1)
            
            label2 = gtk.Label("Mount point: %s" % self.mount_point)
            self.box.add(label2)
        else:
            label = gtk.Label("Not mounted")
            self.box.add(label)

        # add a button for mounting
        btn_mount = gtk.Button("Unmount" if self.loop_dev else "Mount")
        btn_mount.connect('clicked', self.click)
        self.box.add(btn_mount)
        self.show_all()

    def click(self, *args):
        mapper_path = os.path.join('/dev', 'mapper', self.luks_device_name)

        try:
            if self.loop_dev:
                # unmount
                subprocess.check_call(['umount', mapper_path])
                subprocess.check_call(['cryptsetup', 'luksClose', self.luks_device_name])
                subprocess.check_call(['losetup', '-d', self.loop_dev])
                self.loop_dev = None
            else:
                # mount
                subprocess.check_call(['losetup', '-f', self.loopback_file])
                self.loop_dev = get_loopback_device(self.loopback_file)
                open_crypto_dev(self.loop_dev, self.luks_device_name)
                subprocess.check_call(['mount', mapper_path, self.mount_point])
        except UserCancel:
            # raised by open_crypto_dev, undo the loop device
            subprocess.check_call(['losetup', '-d', self.loop_dev])
            self.loop_dev = None
        self.refresh()

    def shutdown(self, widget, data=None):
        '''
        Called by closing the window.
        Return False to allow the shutdown to continue, True otherwise.
        '''
        gtk.main_quit()

class UserCancel(Exception):
    '''
    Raised when a user cancels the input of their LUKS passphrase.
    '''
    pass

def open_crypto_dev(device, luks_name):
    '''
    Display a password dialog, and then use that passphrase to run 
    cryptsetup.  If it returns non-zero, repeat.
    '''
    while True:
        passphrase = prompt_passphrase()
        if not passphrase:
            raise UserCancel()
        proc = subprocess.Popen(['cryptsetup', 'luksOpen', 
            device, luks_name], stdin=subprocess.PIPE)
        proc.communicate(passphrase + '\n') # or is this \r?
        proc.wait()
        if proc.returncode == 0:
            break

def main():
    parser = ConfigParser.SafeConfigParser()
    config_path = os.path.join(os.getenv('HOME'), '.luksmounter')
    if not parser.read(config_path):
        raise Exception('Could not read configuration file: %s' % config_path)
    MounterWindow(parser)
    gtk.main()

if __name__ == '__main__':
    main()