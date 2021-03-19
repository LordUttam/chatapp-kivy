import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
import os, sys
import client
kivy.require('1.11.1')


class connectPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cols = 2
        if os.path.isfile("previous details.txt"):
            with open("previous details.txt", "r") as f:
                d = f.read().split(",")
                prev_ip = d[0]
                prev_port = d[1]
                prev_username = d[2]
        else:
            prev_ip = ''
            prev_port = ''
            prev_username = ''
        self.add_widget(Label(text='IP: '))
        self.ip = TextInput(text=prev_ip, multiline = False)
        self.add_widget(self.ip)

        self.add_widget(Label(text='Port: '))
        self.port = TextInput(text=prev_port, multiline=False)
        self.add_widget(self.port)

        self.add_widget(Label(text='Username: '))
        self.username = TextInput(text=prev_username, multiline=False)
        self.add_widget(self.username)

        self.join = Button(text="Join")
        self.join.bind(on_press=self.join_button)
        self.add_widget(Label())
        self.add_widget(self.join)

    def join_button(self, instance):
        port = self.port.text
        ip = self.ip.text
        username = self.username.text
        # print(f"Attempting to join {ip}:{port} as {username}")

        with open ("previous details.txt","w") as f:
            f.write(f"{ip},{port},{username}")

        info = f"Joining {ip}:{port} as {username}"
        chat_app.info_page.update_info(info)
        chat_app.screen_manager.current = 'Info'
        Clock.schedule_once(self.connect, 1)  # scheduling the actual connection 1 second after the user clicks join

    # Connects to the server
    # (second parameter is the time after which this function had been called,
    #  we don't care about it, but kivy sends it, so we have to receive it)
    def connect(self, _):
        port = int(self.port.text)
        ip = self.ip.text
        username = self.username.text

        if not client.connect(ip, port, username, show_error):
            return
        chat_app.createChatPage()
        chat_app.screen_manager.current = "Chat"


class InfoPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cols = 1

        self.message = Label(halign="center", valign="middle", font_size=30)
        self.message.bind(width=self.update_text_width)

        self.add_widget(self.message)

    def update_info(self, message):
        self.message.text = message

    def update_text_width(self, *_):
        self.message.text_size = (self.message.width * 0.9, None)


class ChatPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1
        self.rows = 2
        # First row is going to be occupied by our scrollable label
        # We want it be take 90% of app height
        self.history = ScrollableLabel(height=Window.size[1] * 0.9, size_hint_y=None)
        self.add_widget(self.history)
        self.new_message = TextInput(width=Window.size[0] * 0.8, size_hint_x=None, multiline=False)
        self.send = Button(text="Send")
        self.send.bind(on_press=self.send_message)
        # To be able to add 2 widgets into a layout with just one collumn, we use additional layout,
        # add widgets there, then add this layout to main layout as second row
        bottom_line = GridLayout(cols=2)
        bottom_line.add_widget(self.new_message)
        bottom_line.add_widget(self.send)
        self.add_widget(bottom_line)

        # Gets called when either Send button or Enter key is being pressed
        # (kivy passes button object here as well, but we don;t care about it)
        # To be able to send message on Enter key, we want to listen to keypresses
        Window.bind(on_key_down=self.on_key_down)

        # We also want to focus on our text input field
        # Kivy by default takes focus out out of it once we are sending message
        # The problem here is that 'self.new_message.focus = True' does not work when called directly,
        # so we have to schedule it to be called in one second
        # The other problem is that schedule_once() have no ability to pass any parameters, so we have
        # to create and call a function that takes no parameters
        Clock.schedule_once(self.focus_text_input, 1)

        client.start_listening(self.incoming_message, show_error)

    def on_key_down(self, instance, keyboard, keycode, text, modifiers):
        if keycode == 40:  # keycode for enter key
            self.send_message(None)

    def send_message(self, _):
        message = self.new_message.text
        self.new_message.text = ''

        if message:
            # Our messages - use red color for the name
            self.history.update_chat_history(f'[color=dd2020]{chat_app.connect_page.username.text}[/color] > {message}')
            client.send(message)

        Clock.schedule_once(self.focus_text_input, 0.1)

    def focus_text_input(self, _):
        self.new_message.focus = True

    def incoming_message(self, username, message):
        self.history.update_chat_history(f"[color=20dd20]{username}[/color] > \n {message}")


class ScrollableLabel(ScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.layout = GridLayout(cols=1, size_hint_y=None)
        self.add_widget(self.layout)
        # Now we need two widgets - Label for chat history and 'artificial' widget below
        # so we can scroll to it every new message and keep new messages visible
        # We want to enable markup, so we can set colors for example
        self.chat_history = Label(size_hint_y=None, markup=True)
        self.scroll_to_point = Label()
        self.layout.add_widget(self.chat_history)
        self.layout.add_widget(self.scroll_to_point)

    def update_chat_history(self, message):
        self.chat_history.text += '\n' + message
        # Set layout height to whatever height of chat history text is + 15 pixels
        # (adds a bit of space at teh bottom)
        # Set chat history label to whatever height of chat history text is
        # Set width of chat history text to 98 of the label width (adds small margins)
        self.layout.height = self.chat_history.texture_size[1] + 15
        self.chat_history.height = self.chat_history.texture_size[1]
        self.chat_history.text_size = (self.chat_history.width * 0.98, None)

        # As we are updating above, text height, so also label and layout height are going to be bigger
        # than the area we have for this widget. ScrollView is going to add a scroll, but won't
        # scroll to the botton, nor is there a method that can do that.
        # That's why we want additional, empty widget below whole text - just to be able to scroll to it,
        # so scroll to the bottom of the layout
        self.scroll_to(self.scroll_to_point)


class chatApp(App):
    def build(self):
        self.screen_manager = ScreenManager()

        self.connect_page = connectPage()
        screen = Screen(name = 'Connect')
        screen.add_widget(self.connect_page)
        self.screen_manager.add_widget(screen)

        self.info_page = InfoPage()
        screen = Screen(name='Info')
        screen.add_widget(self.info_page)
        self.screen_manager.add_widget(screen)

        return self.screen_manager

    def createChatPage(self):
        self.chat_page = ChatPage()
        screen = Screen(name='Chat')
        screen.add_widget(self.chat_page)
        self.screen_manager.add_widget(screen)


def show_error(message):
    chat_app.info_page.update_info(message)
    chat_app.screen_manager.current = 'Info'
    Clock.schedule_once(sys.exit, 10)


if __name__ == "__main__":
    chat_app = chatApp()
    chat_app.run()

