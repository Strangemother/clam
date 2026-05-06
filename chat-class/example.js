const defaults = {
    endpoint: 'http://192.168.50.60:1234/api/v1/chat/',
    model:    'granite-4.0-h-tiny',
}

const chat = new Chat(defaults)

// Override to do something more interesting later, e.g. push to Vue data.
// chat.onResponse = (msg) => { myApp.reply = msg.content }
