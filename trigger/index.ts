// Exemplo minimal: Trigger.dev webhook receiver que, ao receber "start"
// chama a API do Modal ou dispara workflow que provisiona uma execução Modal.


import express from 'express'
import fetch from 'node-fetch'


const app = express()
app.use(express.json())


const MODAL_RUN_ENDPOINT = process.env.MODAL_RUN_ENDPOINT // exemplo
const MODAL_API_KEY = process.env.MODAL_API_KEY


app.post('/start', async (req, res) => {
const { file_id, filename } = req.body
// Aqui você chamaria a API do Modal para criar uma execução passando FILE_URL etc.
const body = {
file_id,
file_url: `https://your-storage.example.com/${filename}`,
callback_url: process.env.MODAL_CALLBACK_URL,
}


const resp = await fetch(MODAL_RUN_ENDPOINT, {
method: 'POST',
headers: {
'Authorization': `Bearer ${MODAL_API_KEY}`,
'Content-Type': 'application/json'
},
body: JSON.stringify(body)
})


const data = await resp.json()
res.json({ ok: true, modal_response: data })
})


app.listen(3000, () => console.log('Trigger mock listening on 3000'))