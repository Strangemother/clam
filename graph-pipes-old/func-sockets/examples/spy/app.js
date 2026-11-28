const log = document.querySelector('#log')
const status = document.querySelector('#status')
const messageCount = document.querySelector('#message-count')
const graphId = document.querySelector('#graph-id')
const message = document.querySelector('#message')

let client
let received = 0

const write = (value) => {
    const line = typeof value === 'string' ? value : JSON.stringify(value)
    log.textContent += `${line}\n`
    log.scrollTop = log.scrollHeight
}

const setStatus = (label, connected = false) => {
    status.textContent = label
    status.classList.toggle('connected', connected)
}

document.querySelector('#connect-form').addEventListener('submit', (event) => {
    event.preventDefault()
    client?.close()
    setStatus('Connecting')

    client = new GraphSocket(graphId.value)
    client.addEventListener('open', () => setStatus('Connected', true))
    client.addEventListener('close', () => setStatus('Disconnected'))
    client.addEventListener('error', () => setStatus('Connection error'))
    client.addEventListener('message', (event) => {
        received += 1
        messageCount.textContent = `${received} message${received === 1 ? '' : 's'}`
        write(event.detail)
    })
    client.connect()
})

document.querySelector('#send-form').addEventListener('submit', (event) => {
    event.preventDefault()
    if (!client) {
        write('Connect to a graph room before sending.')
        return
    }
    try {
        client.send(message.value)
    } catch (error) {
        write(error.message)
    }
})
