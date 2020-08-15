import requests
import tkinter as tk
import colorsys
import json
import threading
import queue
import re


class main_window:
    def __init__(self, master):
        self.power = tk.StringVar()
        self.power.set('true')
        self.realtime = tk.BooleanVar()
        self.master = master
        master.title("DeskHue")
        master.geometry('545x220')
        # master.iconbitmap('icon.xbm')
        master.resizable(False, False)

        self.hue_label = tk.Label(text="Hue")
        self.saturation_label = tk.Label(text="Saturation")
        self.brightness_label = tk.Label(text="Brightness")
        self.color_label = tk.Label(width=20, height=10, background='white', borderwidth=2, relief=tk.RAISED)
        self.hue_scale = tk.Scale(from_=0, to=65535, orient=tk.HORIZONTAL, command=self.color_label_update)
        self.saturation_scale = tk.Scale(from_=0, to=254, orient=tk.HORIZONTAL, command=self.color_label_update)
        self.brightness_scale = tk.Scale(from_=0, to=254, orient=tk.HORIZONTAL, command=self.color_label_update)
        self.send_button = tk.Button(text="Send", command=main_bridge.send, state=tk.DISABLED) # Grays out send until Configure is pressed
        self.scan_button = tk.Button(text="Scan", state=tk.DISABLED, command=main_bridge.scan)
        self.configuration_button = tk.Button(text="Configuration", command=self.open_configuration_window)
        self.realtime_check = tk.Checkbutton(text="Realtime", variable=self.realtime, state=tk.DISABLED) # Grays out Realtime until Scan is pressed
        self.power_check = tk.Checkbutton(text="Power", onvalue='true', offvalue='false', variable=self.power, state=tk.DISABLED)  # Grays out Power until Scan is pressed
        self.brightness_scale.set(254)

        # Render labels for Hue, Saturation, and Brightness
        labels = [self.hue_label, self.saturation_label, self.brightness_label]
        for index, label in enumerate(labels):
            label.grid(row=index, column=0, padx=10, pady=5)

        # Render sliders for Hue, Saturation, and Brightness
        scales = [self.hue_scale, self.saturation_scale, self.brightness_scale]
        for index, scale in enumerate(scales):
            scale.grid(row=index, column=1, padx=5, pady=5)

        # Render widgets
        self.color_label.grid(row=0, rowspan=3, column=2, padx=5, pady=10)
        self.send_button.grid(row=1, column=3, padx=5, pady=5)
        self.realtime_check.grid(row=1, column=4)
        self.power_check.grid(row=1, column=5)
        self.scan_button.grid(row=0, column=3, columnspan=3)
        self.configuration_button.grid(row=3, column=2, pady=5)

    def hsb_to_rgb(self, hue, saturation, brightness):  # Convert normalized hue, saturation, and brightness into 24 bit rgb
        rgb_normalized = colorsys.hsv_to_rgb(hue, saturation, brightness)
        rgb_denormalized = tuple([254*x for x in rgb_normalized])
        rgb_rounded = tuple([round(x) if isinstance(x, float) else x for x in rgb_denormalized])
        return rgb_rounded

    def color_label_update(self, value):  # Update color_label to current values of the hsb scales
        hue_value = self.hue_scale.get() / 65535
        saturation_value = self.saturation_scale.get() / 254
        brightness_value = self.brightness_scale.get() / 254
        self.color_label.config(bg='#%02x%02x%02x' % self.hsb_to_rgb(hue_value, saturation_value, brightness_value))

    def open_configuration_window(self):
        self.configuration_window = tk.Toplevel(self.master)
        self.config_window = configuration_window(self.configuration_window)



class configuration_window:
    def __init__(self, master):
        self.master = master
        master.focus()
        master.grab_set()
        master.title("Configuration")
        master.geometry('535x190')
        # master.iconbitmap('icon.ico')
        master.resizable(False, False)
        
        self.ip_button = tk.Button(master, text="Search network for bridge", command=self.find_ip)
        self.ip_manual_entry = tk.Entry(master, width=15, insertwidth=1, font='courier')
        self.whitelist_button = tk.Button(master, text="Connect", command=main_bridge.whitelist, state=tk.DISABLED)  # Disable connect button until IP is provided
        self.debug_text = tk.Text(master, width=40, height=9, state=tk.DISABLED, wrap=tk.NONE)
        self.vertical_scroll = tk.Scrollbar(master, command=self.debug_text.yview)
        self.horizontal_scroll = tk.Scrollbar(master, command=self.debug_text.xview, orient=tk.HORIZONTAL)
        self.debug_text.config(yscrollcommand=self.vertical_scroll.set, xscrollcommand=self.horizontal_scroll.set)

        self.ip_manual_entry.insert(tk.END, "Manual IP")
        self.ip_manual_entry.bind("<FocusIn>", self.select_all)

        self.ip_button.grid(row=0, column=0, padx=10, pady=10)
        self.ip_manual_entry.grid(row=1, column=0, padx=10, pady=10)
        self.whitelist_button.grid(row=2, column=0, padx=10, pady=10)
        self.debug_text.grid(row=0, column=1, rowspan=3, pady=(10, 0), padx=(10, 0))
        self.vertical_scroll.grid(row=0, column=2, rowspan=3, pady=(10, 0), sticky='ns')
        self.horizontal_scroll.grid(row=3, column=1, padx=(10, 0), sticky='ew')

        reg = master.register(self.input_validation)
        self.ip_manual_entry.config(validate='key', validatecommand=(reg, '%P'))

        if configuration.exists():
            self.given_stored_configuration()

    def given_stored_configuration(self):
        main_bridge.ip = configuration.get_stored_ip()
        main_bridge.username = configuration.get_stored_username()
        self.add_debug_entry("Stored configuration loaded, IP: {}, Username: {}\n".format(configuration.get_stored_ip(), configuration.get_stored_username()))
        self.ip_manual_entry.delete(0, tk.END)
        self.ip_manual_entry.insert(tk.END, configuration.get_stored_ip())
        self.successful_connection()

    def add_debug_entry(self, entry):
        self.debug_text.config(state=tk.NORMAL)
        self.debug_text.insert(tk.END, entry)
        self.debug_text.config(state=tk.DISABLED)
        
    def enable_connect_button(self):
        self.whitelist_button.config(state=tk.NORMAL)

    def input_validation(self, text):  # Only allow numbers and periods within the manual IP entry
        self.enable_connect_button()
        return not bool(re.compile(r'[^0-9.]').search(text))

    def select_all(self, event):
        self.ip_manual_entry.select_range(0, tk.END)
        self.ip_manual_entry.icursor(tk.END)

    def process_queue(self):
        try:
            message = self.queue.get(0)
        except queue.Empty:
            self.master.after(100, self.process_queue)

    def find_ip(self):
        self.add_debug_entry("Finding bridge on network...\n")
        self.ip_button.config(state=tk.DISABLED)
        self.queue = queue.Queue()
        threaded_ip_finder(self.queue).start()
        self.master.after(100, self.process_queue)

    def successful_connection(self):
        window.scan_button.config(state=tk.NORMAL)


class threaded_ip_finder(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        try:
            main_bridge.find_ip()
            self.queue.put("IP address has been found")
            window.config_window.ip_manual_entry.delete(0, tk.END)
            window.config_window.ip_manual_entry.insert(tk.END, main_bridge.get_ip())
            window.config_window.add_debug_entry("Bridge found on network.\n")
        except requests.exceptions.ConnectionError:  # If bridge can not be found on network
            window.config_window.add_debug_entry("Could not find bridge on network\n")
        window.config_window.ip_button.config(state=tk.NORMAL)


class bridge:
    def __init__(self):
        self.ip = ''
        self.username = ''

    def find_ip(self):
        ip_url = 'https://discovery.meethue.com'
        g = requests.get(ip_url)
        output = g.content  # Creates list with dictionary containing json values
        output_json = json.loads(output)[0]  # Extracts the json from the list, creating a dictionary
        self.ip = output_json.get('internalipaddress')  # Returns the IP string from the dictionary

    def get_ip(self):
        return self.ip

    def get_username(self):
        return self.username

    def whitelist(self):
        data = '{"devicetype":"desk_hue"}'
        url = 'http://{}/api'.format(window.config_window.ip_manual_entry.get())
        p = requests.post(url, data=data)
        try:
            if 'success' in p.text:
                output = p.content
                output_json = json.loads(output)[0]
                self.username = output_json['success']['username']
                window.config_window.add_debug_entry("Success!\n")
                configuration.store_configuration(self.ip, self.username)
                window.config_window.successful_connection()
            elif 'link button not pressed' in p.text:
                window.config_window.add_debug_entry("Link button not pressed.\n")
            else:
                window.config_window.add_debug_entry("Something went wrong...\n")
        except requests.exceptions.ConnectionError:
            window.config_window.add_debug_entry("Connection error, try again.\n")

    def scan(self):
        self.option_menu_light = tk.StringVar()
        self.option_menu_light.set('Select light')

        url = 'http://{}/api/{}/lights'.format(self.get_ip(), self.get_username())
        g = requests.get(url)
        self.light_setup = json.loads(g.content)

        window.send_button.config(state=tk.NORMAL)  # Enable "Send" button
        window.power_check.config(state=tk.NORMAL)  # Enable "Power" checkbox

        window.option_menu = tk.OptionMenu(window.master, self.option_menu_light, *self.light_dictionary().keys())  # Render dropdown menu with lights
        window.option_menu.grid(row=2, column=3, columnspan=3)

    def light_dictionary(self):
        dictionary = {}
        output_key = 1
        for output_key in self.light_setup:
            output_value = self.light_setup['{}'.format(str(output_key))]['name']
            dictionary[output_value] = output_key
            output_key = (int(output_key) + 1)
        return(dictionary)

    def send(self):
        url = 'http://{}/api/{}/lights/{}/state'.format(self.ip, self.username, str(self.light_dictionary()[self.option_menu_light.get()]))
        data = '{"on":' + window.power.get() + ', "hue":' + str(window.hue_scale.get()) + ', "bri":' + str(window.brightness_scale.get()) + ', "sat":' + str(window.saturation_scale.get()) + '}'
        p = requests.put(url, data=data)
        window.realtime_check.config(state=tk.NORMAL)

    def realtime(self):
        if window.realtime.get():
            self.send()
        window.master.after(100, self.realtime)


class stored_configuration:
    def __init__(self):
        pass

    def store_configuration(self, ip, username):
        configuration_file = open('configuration.json', 'w')
        data = {'ip':ip, 'username':username}
        json_object = json.dumps(data, indent=4)
        configuration_file.write(json_object)
        configuration_file.close()

    def get_stored_ip(self):
        configuration_file = open('configuration.json', 'r')
        data = json.load(configuration_file)
        ip = data['ip']
        return ip

    def get_stored_username(self):
        configuration_file = open('configuration.json', 'r')
        data = json.load(configuration_file)
        username = data['username']
        return username

    def exists(self):
        try:
            configuration_file = open('configuration.json', 'r')
            data = json.load(configuration_file)
            if 'ip' in data and 'username' in data:
                return True
            else:
                return False
        except:  # If attempting to open the configuration file produces errors, create a new, blank one
            configuration_file = open('configuration.json', 'w')
            configuration_file.close()
            return False



main_bridge = bridge()
configuration = stored_configuration()

root = tk.Tk()
window = main_window(root)
root.after(1000, main_bridge.realtime)

root.mainloop()

