/* global Chart */
/* eslint-env jquery */
/* eslint-env browser */

'use strict'

let view = null
let idxUUID = 'None'
const canvas = document.getElementById('canvas')
let mode = 'task'
const config = {}

function shouldUseAppBridge () {
  return typeof window.pywebview !== 'undefined' &&
    window.pywebview !== null &&
    typeof window.pywebview.api !== 'undefined' &&
    window.pywebview.api !== null &&
    typeof window.pywebview.api.open_url === 'function'
}

function openExternalUrl (url) {
  if (shouldUseAppBridge()) {
    window.pywebview.api.open_url(url).catch(function (error) {
      console.error('Failed to open external URL via app bridge', error)
      if (typeof url === 'string' && url.startsWith('things:///')) {
        window.location.href = url
      }
    })
    return false
  }
  if (typeof url === 'string' && url.startsWith('things:///')) {
    window.location.href = url
    return false
  }
  window.open(url, '_blank')
  return false
}

function isExternalUrl (url) {
  return typeof url === 'string' &&
    (url.startsWith('things:///') || url.startsWith('http://') || url.startsWith('https://'))
}

function handleExternalLink (event, url) {
  if (!isExternalUrl(url)) {
    return true
  }
  if (event != null) {
    event.preventDefault()
    event.stopPropagation()
  }
  openExternalUrl(url)
  return false
}

function round (value, precision) {
  const multiplier = Math.pow(10, precision || 0)
  return Math.round(value * multiplier) / multiplier
}

function kanbanHide () { document.getElementById('content').style.display = 'none' }
function kanbanShow () { preferencesHide(); statsHide(); document.getElementById('content').style.display = '' }

const arrSum = arr => arr.reduce((a, b) => a + b, 0)

function isElementInViewport (el) {
  if (typeof jQuery === 'function' && el instanceof jQuery) { el = el[0] }
  const rect = el.getBoundingClientRect()
  return (
    rect.top >= document.getElementById('header').offsetHeight &&
    rect.left >= 0 &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && /* or $(window).height() */
    rect.right <= (window.innerWidth || document.documentElement.clientWidth) /* or $(window).width() */
  )
}

function kanbanUpdate () {
  view = kanbanUpdate
  statsHide()
  preferencesHide()
  kanbanShow()
  if (canvas == null) {
    requestParallel('api/areas', function (data) { optionsAdd(data, 'areas') })
    requestParallel('api/projects', function (data) { optionsAdd(data, 'projects') })
    requestParallel('api/inbox', function (data) { rowsAdd('color4', 'Inbox', data, 'id=inbox', 'tasks in the inbox', 'i', 'inbox') })
    requestParallel('api/today', function (data) { rowsAdd('color6', 'Today', data, 'id=today', 'tasks for today', 't', 'star') })
    requestParallel(`api/tag/${config.tag_waiting}`, function (data) { rowsAdd('color1', 'Waiting', data, `query=${config.tag_waiting}`, `tasks with the tag "${config.tag_waiting}"`, 'w', 'clock') })
    requestParallel(`api/tag/${config.tag_mit}`, function (data) { rowsAdd('color2', 'MIT', data, `query=${config.tag_mit}`, `most important tasks with the tag "${config.tag_mit}"`, 'm', 'exclamation-triangle') })
    requestParallel('api/upcoming', function (data) { rowsAdd('color5', 'Upcoming', data, 'id=upcoming', 'scheduled tasks', 'u', 'calendar-alt') })
    requestParallel('api/cleanup', function (data) { rowsAdd('color8', 'Grooming', data, '', 'empty projects, tasks with no parent, items with tag "Cleanup"', '', 'broom') })
    requestParallel('api/next', function (data) { rowsAdd('color7', 'Next', data, 'id=anytime', 'anytime tasks that are not in today', 'n', 'forward') })
    requestParallel('api/backlog', function (data) { rowsAdd('color3', 'Backlog', data, 'id=someday', 'tasks in someday projects', 'b', 'paperclip') })
  }
}

function contentReset (id) {
  const filter = document.getElementById(id)
  filter.innerHTML = ''
}

function optionAdd (list, title, uuid, size) {
  const li = document.createElement('li')
  li.innerHTML = `${title} (${size})`

  const a = document.createElement('a')
  a.href = '#'
  a.setAttribute('id', uuid)
  a.onclick = function (event) {
    event.preventDefault()
    highlight(event)
    kanbanFilterChange(this)
    return false
  }
  a.appendChild(li)
  list.appendChild(a)
}

function optionsAdd (data, id) {
  const filter = document.getElementById(id)
  if (filter.childNodes.length === 0) {
    const items = JSON.parse(data.response)
    items.forEach(function (item) {
      optionAdd(filter, item.title, item.uuid, item.size)
    })
  }
}

function contentAdd (req) {
  const elem = document.getElementById('content')
  elem.innerHTML += req
}

function contentReplace (id, data) {
  const elem = document.getElementById(id)
  elem.outerHTML = data
}

function rowAdd (uuid, task, started, due, cssClass, context) {
  return `<div class='box bigger' draggable='false' 
               ondragstart='onDragStart(event);' 
               id='${uuid}'>${task}
            <div class='deadline'>${started}</div>
            <div class='deadline'>${due}</div>
            <div class='area ${cssClass}'>${context}</div>
          </div>
          `
}
function rowsGet (rows) {
  let fragment = ''
  rows.forEach(function (row) {
    let cssClass = 'hasNoProject'
    let task = row.title
    let context = row.context
    let due = ''
    let started = ''

    if (row.type === 'project') {
      task = `${task} (${row.size})`
    }

    if (row.uuid !== null) {
      task = `<a draggable='false' href='things:///show?id=${row.uuid}'
                       onclick='return handleExternalLink(event, this.href)'>${task}
                    </a>`
    }
    if (row.context_uuid !== null) {
      context = `<a draggable='false' 
                          href='things:///show?id=${row.context_uuid}' 
                          onclick='return handleExternalLink(event, this.href)'>
                          ${row.context}
                        </a>`
    }
    if (row.context !== null) {
      cssClass = 'hasProject'
    } else {
      row.context = 'No Context'
    }
    if (row.due !== null && row.due !== undefined) {
      due = `Due: ${row.due}`
      cssClass = 'hasDeadline'
    }
    if (row.started !== null && row.started !== undefined) {
      started = `Start: ${row.started}`
    }

    fragment += rowAdd(row.uuid, task, started, due, cssClass, context)
  })
  return fragment
}

function columnAddPreview (cssclass, header) {
  return `<div class='column' id='${header}'>
                <div class='inner-column'>
                    <h2 class='h2 bigger ${cssclass}'>
                        ${header}<span class='size'></span>
                    </h2>
                </div>
            </div>`
}

function columnAdd (title, help, query, shortcut, color, size, rowHTML, icon) {
  if (query !== '') {
    query = `href="things:///show?${query}" onclick="return handleExternalLink(event, this.href)"`
  }
  return `
        <div class='column' 
            ondrop='onDrop(event);'
            ondragleave='onDragLeave(event);'
            ondragover='onDragOver(event);'
            id='${title}' title='${help}'>
            <div class='inner-column'>
                <a draggable='false' 
                    ${query}
                    accesskey='${shortcut}'
                    title='⌃+⎇+${shortcut}'>
                    <h2 class='h2 bigger ${color}'><i class="fa fa-${icon}"></i> ${title}
                        <span class='size'>${size}</span>
                    </h2>
                </a>
                ${rowHTML}
            </div>
        </div>
        `
}

function rowsAdd (color, title, data, query, help, shortcut, icon) {
  const rows = JSON.parse(data.response)
  const rowHTML = rowsGet(rows)
  const fragment = columnAdd(title, help, query, shortcut, color, rows.length, rowHTML, icon)

  if (document.getElementById(title) !== null) {
    contentReplace(title, fragment)
  } else {
    document.getElementById('loading').style.display = 'none'
    contentAdd(fragment)
  }
}

const requestParallel = function (url, method) {
  const request = new XMLHttpRequest()
  request.onreadystatechange = function () {
    if (request.readyState !== 4) { return }
    if (request.status >= 200 && request.status < 300) {
      if (method !== null) { method(request) }
    } else {
      console.log('Error: ' + request.status)
    }
  }
  request.open('GET', `${url}?mode=${mode}`, true)
  request.send()
}

const requestSequencial = function (url, method, data) {
  const request = new XMLHttpRequest()
  return new Promise(function (resolve, reject) {
    request.onreadystatechange = function () {
      if (request.readyState !== 4) { return }
      if (request.status >= 200 && request.status < 300) {
        resolve(request)
      } else {
        reject(new Error(request.statusText))
      }
    }
    request.open(method || 'GET', `${url}?mode=${mode}`, true)
    request.send(data || null)
  })
}

function refresh () {
  if (view != null) {
    view()
  } else {
    kanbanUpdate()
  }
}

function onDragStart (event) { // eslint-disable-line no-unused-vars
  event
    .dataTransfer
    .setData('text/plain', event.target.id)

  event
    .currentTarget
    .style
    .border = '2px solid green'
}

function onDragOver (event) { // eslint-disable-line no-unused-vars
  event.preventDefault()
  event
    .currentTarget
    .style
    .border = '2px solid red'
}

function onDragLeave (event) { // eslint-disable-line no-unused-vars
  event.preventDefault()
  event
    .currentTarget
    .style
    .border = '0'
}

function onDrop (event) { // eslint-disable-line no-unused-vars
  // not completely implemented yet
  event.preventDefault()
  event
    .currentTarget
    .style
    .border = '0'

  const id = event
    .dataTransfer
    .getData('text')

  const draggableElement = document.getElementById(id)
  const dropzone = event.target

  draggableElement
    .style
    .border = '0'

  dropzone.appendChild(draggableElement)

  event
    .dataTransfer
    .clearData()

  console.log(dropzone.id)
  // refresh();
}

function switchMode (event) { // eslint-disable-line no-unused-vars
  const taskMode = document.getElementById('mode').checked
  if (taskMode === true) {
    mode = 'task'
  } else {
    mode = 'project'
  }
  refresh()
}

function kanbanFilterChange (event) { // eslint-disable-line no-unused-vars
  const uuid = event.id
  const filterType = event.parentNode.dataset.ctx
  if (uuid != null) {
    idxUUID = uuid

    if (idxUUID !== 'None' && filterType != null) {
      requestParallel('api/filter/' + filterType + '/' + idxUUID, refresh)
    } else {
      idxUUID = 'None'
      kanbanFilterReset()
    }
    kanbanUpdate()
  }
}

function kanbanFilterReset () {
  requestParallel('api/filter/reset', refresh)
}

function preferencesHide () {
  document.getElementById('prefs').style.display = 'none'
}
function preferencesShow () {
  statsHide()
  kanbanHide()
  document.getElementById('prefs').style.display = ''
}
function statsHide () {
  document.getElementById('stats').style.display = 'none'
}
function statsShow () {
  preferencesHide()
  kanbanHide()
  document.getElementById('stats').style.display = ''
}
function statsReplace (canv) {
  contentReset('stats')
  document.getElementById('stats').appendChild(canv)
}
function canvasCreate () {
  const canvas = document.createElement('canvas')
  canvas.id = 'canvas'
  canvas.className = 'canvas'
  return canvas
}

async function statsShowDistribution () {
  view = statsShowDistribution // eslint-disable-line no-unused-vars
  kanbanHide()
  statsShow()
  const canv = canvasCreate()
  statsReplace(canv)

  const ctx = canv.getContext('2d')
  let backlog = 0
  await requestSequencial('api/backlog').then(function (data) {
    backlog = JSON.parse(data.response).length
  })
  let upcoming = 0
  await requestSequencial('api/upcoming').then(function (data) {
    upcoming = JSON.parse(data.response).length
  })
  let inbox = 0
  await requestSequencial('api/inbox').then(function (data) {
    inbox = JSON.parse(data.response).length
  })
  let today = 0
  await requestSequencial('api/today').then(function (data) {
    today = JSON.parse(data.response).length
  })
  let next = 0
  await requestSequencial('api/next').then(function (data) {
    next = JSON.parse(data.response).length
  })
  new Chart(ctx, { // eslint-disable-line no-new
    type: 'doughnut',
    options: {
      plugins: {
        labels: {
          render: 'percentage',
          precision: 0,
          position: 'outside',
          arc: true
        }
      }
    },
    data: {
      labels: [`Backlog (${backlog})`, `Upcoming (${upcoming})`, `Inbox  (${inbox})`, `Today (${today})`, `Next  (${next})`],
      datasets: [
        {
          label: '# of tasks',
          data: [backlog, upcoming, inbox, today, next],
          backgroundColor: [
            'rgba(255, 99, 132, 0.2)',
            'rgba(54, 162, 235, 0.2)',
            'rgba(255, 206, 86, 0.2)',
            'rgba(75, 192, 192, 0.2)',
            'rgba(153, 102, 255, 0.2)',
            'rgba(255, 159, 64, 0.2)'
          ],
          borderColor: [
            'rgba(255, 99, 132, 1)',
            'rgba(54, 162, 235, 1)',
            'rgba(255, 206, 86, 1)',
            'rgba(75, 192, 192, 1)',
            'rgba(153, 102, 255, 1)',
            'rgba(255, 159, 64, 1)'
          ],
          borderWidth: 1
        }
      ]
    }
  })
}

function matrixAdd (cssClass, color, title, query, help, shortcut, icon) {
  if (query !== '') {
    query = `href="things:///show?${query}"`
  }
  const fragment = `
        <div class='${cssClass}' id='${title}'>
                <a draggable='false' 
                    ${query}
                    target='_blank'
                    accesskey='${shortcut}'
                    title='⌃+⎇+${shortcut}'>
                    <h2 class='h2 bigger ${color}'><i class="fa fa-${icon}"></i> ${title}</h2>
                </a>
                <div id='${title}-inner' class='eisenhower-inner' title='${help}'>
                Loading...
                </div>
            </div>
        </div>`
  return fragment
}

function matrixReplace (id, data) {
  const html = rowsGet(JSON.parse(data.response))
  document.getElementById(id + '-inner').innerHTML = html
}

async function statsShowSeinfeld () {
  view = statsShowSeinfeld // eslint-disable-line no-unused-vars
  kanbanHide()
  statsShow()

  let fragment = ''
  let id = ''
  for (let i = 0; i <= 66; i++) {
    id = new Date(new Date().setDate(new Date().getDate() - i)).toISOString().split('T')[0]
    fragment += `<div class='seinfeld-inner' id='seinfeld-${id}' title='${id}'></div>`
  }

  // color3 = gray
  // color6 = green
  // color2 = red

  const content = `
    <div id='seinfeld-outer' class='seinfeld-outer'>
      <div class="title">Seinfeld Calendar / 66 Day Challenge</div>
      <p>Every day you finish or cancel an accordingly tagged task within the last 66 days, you'll color a circle in this diagram. Don't break the chain!</p>
      ${fragment}
    </div>`

  const canv = document.createElement('div')
  canv.id = 'canvas'
  canv.className = 'canvas container seinfeld'
  canv.innerHTML = content
  statsReplace(canv)

  requestSequencial(`api/seinfeld/${config.tag_seinfeld}`).then(function (data) {
    data = JSON.parse(data.response)
    data.forEach(function (item) {
      id = item.stop_date
      if (item.status === 'completed') {
        document.getElementById(`seinfeld-${id}`).classList.add('hasProject')
      } else {
        document.getElementById(`seinfeld-${id}`).classList.add('hasDeadline')
      }
    })
  })
}

async function statsShowMinutes () {
  view = statsShowMinutes // eslint-disable-line no-unused-vars
  kanbanHide()
  statsShow()

  const canv = document.createElement('div')
  canv.id = 'canvas'
  canv.className = 'canvas container eisenhower'
  canv.innerHTML = matrixAdd('Time', 'color3', 'Time', '', '', 'T', 'clock') +
                   matrixAdd('A', 'color8', 'A', `query=${config.A}`, `tasks today with tag ${config.A}`, 'A', 'fire') +
                   matrixAdd('B', 'color2', 'B', `query=${config.B}`, `tasks today with tag ${config.B}`, 'B', 'exclamation-circle') +
                   matrixAdd('C', 'color5', 'C', `query=${config.C}`, `tasks today with tag ${config.C}`, 'C', 'hands-helping') +
                   matrixAdd('D', 'color3', 'D', `query=${config.D}`, `tasks today with tag ${config.D}`, 'D', 'trash')
  statsReplace(canv)

  requestParallel('api/filter/reset', null)
  requestSequencial(`api/tag/${config.A}`).then(function (data) { matrixReplace('A', data) })
  requestSequencial(`api/tag/${config.B}`).then(function (data) { matrixReplace('B', data) })
  requestSequencial(`api/tag/${config.C}`).then(function (data) { matrixReplace('C', data) })
  requestSequencial(`api/tag/${config.D}`).then(function (data) { matrixReplace('D', data) })
  requestSequencial('api/stats-min-today').then(function (data) {
    const jsonfile = JSON.parse(data.response)
    let minutes = jsonfile[0].minutes
    if (minutes == null) {
      minutes = 'no time estimations'
    } else if (minutes === 60) {
      minutes = round(minutes / 60) + ' hour today'
    } else {
      minutes = round(minutes / 60, 1) + ' hours today'
    }
    document.getElementById('Time-inner').innerHTML = minutes
  })
}

async function statsShowUniverse () {
  view = statsShowUniverse // eslint-disable-line no-unused-vars
  kanbanHide()
  statsShow()
  const canv = canvasCreate()
  statsReplace(canv)
  const ctx = canv.getContext('2d')

  await requestSequencial('api/top-proj').then(function (data) {
    const jsonfile = JSON.parse(data.response)

    const labels = jsonfile.map(function (e) {
      return e.title
    })
    const uuids = jsonfile.map(function (e) {
      return e.uuid
    })
    const x = jsonfile.map(function (e) {
      return e.created
    })
    const y = jsonfile.map(function (e) {
      return e.modified
    })
    const r = jsonfile.map(function (e) {
      return e.tasks
    })

    const xMax = Math.max(...x)
    const yMax = Math.max(...y)
    const rMax = Math.max(...r)
    const chartData = []

    for (let i = 0; i < labels.length; i++) {
      const chartDataset = {
        label: labels[i],
        backgroundColor: 'rgba(' + (r[i] / rMax) * 250 + ', 150, 0, 0.5)',
        borderColor: 'rgba(150, 150, 0, 1)',
        borderWidth: 1,
        hoverBorderWidth: 2,
        rotation: uuids[i],
        data: [
          {
            x: (x[i] / xMax) * 10,
            y: (y[i] / yMax) * 10,
            r: (r[i] / rMax) * 50
          }
        ]
      }

      chartData.push(chartDataset)
    }

    const dataset = { datasets: chartData }
    const options = {
      title: { display: true, text: 'project size vs. age' },
      legend: { display: false },
      scales: {
        yAxes: [
          {
            scaleLabel: { display: true, labelString: 'age [modified]' },
            ticks: { display: false, max: 10.1 }
          }
        ],
        xAxes: [
          {
            scaleLabel: { display: true, labelString: 'age [created]' },
            ticks: { display: false, max: 10.5 }
          }
        ]
      }
    }

    const chart = new Chart(ctx, { // eslint-disable-line no-new
      type: 'bubble',
      data: dataset,
      options: options
    })
    document.getElementById('canvas').addEventListener('click', function (evt) {
      const activePoint = chart.getDatasetAtEvent(evt)
      if (activePoint.length === 0) {
        return
      }
      const uuid = activePoint[0]._options.rotation
      openExternalUrl(`things:///show?id=${uuid}`)
    })
  })
}

async function statsShowHistory () {
  view = statsShowHistory // eslint-disable-line no-unused-vars
  kanbanHide()
  statsShow()
  const canv = canvasCreate()
  statsReplace(canv)

  await requestSequencial('api/stats-day').then(function (data) {
    const jsonfile = JSON.parse(data.response)

    const labels = jsonfile.map(function (e) {
      return e.date
    })
    const created = jsonfile.map(function (e) {
      return e.created
    })
    const cancelled = jsonfile.map(function (e) {
      return e.cancelled
    })
    const completed = jsonfile.map(function (e) {
      return e.completed
    })
    const trashed = jsonfile.map(function (e) {
      return e.trashed
    })

    const ctx = canv.getContext('2d')
    const config = {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'created (' + arrSum(created) + ')',
            data: created,
            backgroundColor: 'rgba(0, 119, 204, 0.5)',
            borderColor: 'rgba(0, 119, 204, 1)',
            borderWidth: 1
          },
          {
            label: 'completed (' + arrSum(completed) + ')',
            data: completed,
            backgroundColor: 'rgba(0, 204, 119, 0.5)',
            borderColor: 'rgba(0, 204, 119, 1)',
            borderWidth: 1
          },
          {
            label: 'cancelled (' + arrSum(cancelled) + ')',
            data: cancelled,
            backgroundColor: 'rgba(204, 119, 0, 0.5)',
            borderColor: 'rgba(204, 119, 0, 1)',
            borderWidth: 1
          },
          {
            label: 'trashed (' + arrSum(trashed) + ')',
            data: trashed,
            backgroundColor: 'rgba(204, 0, 119, 0.5)',
            borderColor: 'rgba(204, 0, 119, 1)',
            borderWidth: 1
          }
        ]
      },
      options: {
        plugins: {
          labels: false
        },
        scales: {
          xAxes: [
            {
              stacked: true
            }
          ],
          yAxes: [
            {
              stacked: true
            }
          ]
        }
      }
    }
    new Chart(ctx, config) // eslint-disable-line no-new
  })
}

function highlight (event) {
  $('#listContainer').find('*').removeClass('active')
  $('#' + event.currentTarget.id + ' :first-child').addClass('active')
  if (event.type === 'click') {
    // const isVisible = $('#' + event.currentTarget.id).is(':in-viewport')
    const isVisible = isElementInViewport(event.currentTarget)
    if (isVisible === false) {
      event.currentTarget.scrollIntoView()
    }
  }
}

$(document).ready(function () {
  $('li').eq(0).addClass('active')
  $('.cardATags').eq(0).focus()
  $('#listContainer').find('a').on('click', function (event) {
    highlight(event)
  })
  document.addEventListener('click', function (event) {
    const link = event.target.closest('a[href]')
    if (link == null) {
      return
    }
    const href = link.getAttribute('href')
    if (href === '#' || href.startsWith('javascript:')) {
      event.preventDefault()
      return
    }
    if (href == null || !isExternalUrl(href)) {
      return
    }
    event.preventDefault()
    openExternalUrl(href)
  }, true)

  $(document).keyup(function (e) {
    if (view === showPreferences) {
      return
    }
    const liCount = $('li').length
    let curentActive = 0

    let eachCounter = 0
    $('li').each(function () {
      if ($(this).hasClass('active')) {
        curentActive = eachCounter
      }
      eachCounter++
    })

    if (e.keyCode === 37) { // left
      curentActive -= 1
    } else if (e.keyCode === 39) { // right
      curentActive += 1
    } if (e.keyCode === 38) { // top
      curentActive -= 1
    } if (e.keyCode === 40) { // bott
      curentActive += 1
    }

    if (e.keyCode >= 37 && e.keyCode <= 40) {
      e.preventDefault()
      if (curentActive === liCount) {
        curentActive = 0
      }
      highlight(e)
      $('li').eq(curentActive).click()
    }
  })
})

async function savePreferences () { // eslint-disable-line no-unused-vars
  view = showPreferences
  kanbanHide()
  statsHide()
  preferencesShow()
  await requestSequencial('config/TAG_MIT', 'PUT', document.getElementById('pref-mit').value).then(readPreferences())
  await requestSequencial('config/TAG_WAITING', 'PUT', document.getElementById('pref-waiting').value).then(readPreferences())
  await requestSequencial('config/TAG_CLEANUP', 'PUT', document.getElementById('pref-cleanup').value).then(readPreferences())
  await requestSequencial('config/TAG_SEINFELD', 'PUT', document.getElementById('pref-seinfeld').value).then(readPreferences())
  await requestSequencial('config/TAG_A', 'PUT', document.getElementById('pref-A').value).then(readPreferences())
  await requestSequencial('config/TAG_B', 'PUT', document.getElementById('pref-B').value).then(readPreferences())
  await requestSequencial('config/TAG_C', 'PUT', document.getElementById('pref-C').value).then(readPreferences())
  await requestSequencial('config/TAG_D', 'PUT', document.getElementById('pref-D').value).then(readPreferences())
  await requestSequencial('config/STAT_DAYS', 'PUT', document.getElementById('pref-statdays').value).then(readPreferences())
  await requestSequencial('config/API_EXPOSE', 'PUT', document.getElementById('pref-expose').checked).then(readPreferences())
  await requestSequencial('config/KANBANVIEW_PORT', 'PUT', document.getElementById('pref-port').value).then(readPreferences())
}

async function alertPreferences () { // eslint-disable-line no-unused-vars
  await requestSequencial('api/reset', 'PUT', document.getElementById('pref-reset').value).then(readPreferences())
  alert('Please restart KanbanView now')
}

async function alertFeedback () { // eslint-disable-line no-unused-vars
  await requestSequencial('api/feedback', 'PUT', document.getElementById('pref-feedback').value).then(readPreferences())
  alert('Please switch to your email application now')
}

async function showPreferences () { // eslint-disable-line no-unused-vars
  view = showPreferences
  kanbanHide()
  statsHide()
  preferencesShow()
  const prefs = document.getElementById('prefs')

  const prefDB = rowAdd(null, 'MIT Tag: <input class="pref-input" id="pref-mit" onchange="javascript:savePreferences();">', 'Tasks with this tag will be shown in the Most Important Task column.', '', '', '') +
                 rowAdd(null, 'Waiting Tag: <input class="pref-input" id="pref-waiting" onchange="javascript:savePreferences();">', 'Tasks with this tag will be shown in the Waiting column.', '', '', '') +
                 rowAdd(null, 'Cleanup Tag: <input class="pref-input" id="pref-cleanup" onchange="javascript:savePreferences();">', 'Tasks with this tag will be shown in the Grooming column.', '', '', '') +
                 rowAdd(null, 'Seinfeld Tag: <input class="pref-input" id="pref-seinfeld" onchange="javascript:savePreferences();">', 'Tasks with this tag will be shown in the Seinfeld view.', '', '', '') +
                 rowAdd(null, 'Eisenhower "A" Tag: <input class="pref-input" id="pref-A" onchange="javascript:savePreferences();">', 'Tasks with this tag will be shown in the A quadrant of the Eisenhower view (urgent and important).', '', '', '') +
                 rowAdd(null, 'Eisenhower "B" Tag: <input class="pref-input" id="pref-B" onchange="javascript:savePreferences();">', 'Tasks with this tag will be shown in the B quadrant of the Eisenhower view (not urgent and important).', '', '', '') +
                 rowAdd(null, 'Eisenhower "C" Tag: <input class="pref-input" id="pref-C" onchange="javascript:savePreferences();">', 'Tasks with this tag will be shown in the C quadrant of the Eisenhower view (urgent and not important).', '', '', '') +
                 rowAdd(null, 'Eisenhower "D" Tag: <input class="pref-input" id="pref-D" onchange="javascript:savePreferences();">', 'Tasks with this tag will be shown in the D quadrant of the Eisenhower view (not urgent and not important).', '', '', '') +
                 rowAdd(null, 'Days for history view: <input class="pref-input" id="pref-statdays" onchange="javascript:savePreferences();">', 'How many days the statistic view should consider (currently the app has to be restarted to take this preference to take effect).', '', '', '')
  const prefAPI = rowAdd(null, 'Expose API to network: <input class="pref-input" id="pref-expose" type="checkbox" onchange="javascript:savePreferences();">', 'If enabled, you can open the GUI by devices within your network, e.g. via an iPad by opening this link and saving it to the home screen: <i class="fa fa-external-link-alt"></i> <a id="host" href="#"></a>.', '', '', '') +
                  rowAdd(null, 'PORT: <input class="pref-input" id="pref-port" onchange="javascript:savePreferences();">', 'TCP port the API is listening at.', '', '', '') +
                  rowAdd(null, '<input type="button" class="pref-input" id="pref-reset" onclick="javascript:alertPreferences();" value="Reset Configuration">', 'Current DB: ' + config.thingsdb, '', '', '') +
                  rowAdd(null, '<input type="button" class="pref-input" id="pref-feedback" onclick="javascript:alertFeedback();" value="Send Feedback">', 'Send debug reports or future requests', '', '', '')

  prefs.innerHTML = columnAdd('Database', 'Database', '', '', 'color2', '', prefDB, 'database') +
                    columnAdd('API', 'API', '', '', 'color3', '', prefAPI, 'wifi')

  await readPreferences()
  document.getElementById('pref-mit').value = config.tag_mit
  document.getElementById('pref-waiting').value = config.tag_waiting
  document.getElementById('pref-cleanup').value = config.tag_cleanup
  document.getElementById('pref-seinfeld').value = config.tag_seinfeld
  document.getElementById('pref-A').value = config.A
  document.getElementById('pref-B').value = config.B
  document.getElementById('pref-C').value = config.C
  document.getElementById('pref-D').value = config.D
  document.getElementById('pref-statdays').value = config.statdays
  document.getElementById('pref-expose').checked = config.api_expose
  document.getElementById('pref-port').value = config.api_port
  document.getElementById('host').innerHTML = config.api_url
  document.getElementById('host').href = config.api_url
}

async function readPreferences () {
  await requestSequencial('config/THINGSDB').then(function (data) { config.thingsdb = data.response })
  await requestSequencial('config/TAG_MIT').then(function (data) { config.tag_mit = data.response })
  await requestSequencial('config/TAG_WAITING').then(function (data) { config.tag_waiting = data.response })
  await requestSequencial('config/TAG_CLEANUP').then(function (data) { config.tag_cleanup = data.response })
  await requestSequencial('config/TAG_SEINFELD').then(function (data) { config.tag_seinfeld = data.response })
  await requestSequencial('config/TAG_A').then(function (data) { config.A = data.response })
  await requestSequencial('config/TAG_B').then(function (data) { config.B = data.response })
  await requestSequencial('config/TAG_C').then(function (data) { config.C = data.response })
  await requestSequencial('config/TAG_D').then(function (data) { config.D = data.response })
  await requestSequencial('config/STAT_DAYS').then(function (data) { config.statdays = data.response })
  await requestSequencial('config/API_EXPOSE').then(function (data) { config.api_expose = (data.response.toLowerCase() === 'true') })
  await requestSequencial('config/KANBANVIEW_PORT').then(function (data) { config.api_port = data.response })
  await requestSequencial('api/url').then(function (data) { config.api_url = data.response })
}

window.onload = async function () {
  contentAdd(columnAddPreview('color1', 'Backlog'))
  contentAdd(columnAddPreview('color8', 'Grooming'))
  contentAdd(columnAddPreview('color5', 'Upcoming'))
  contentAdd(columnAddPreview('color3', 'Waiting'))
  contentAdd(columnAddPreview('color4', 'Inbox'))
  contentAdd(columnAddPreview('color2', 'MIT'))
  contentAdd(columnAddPreview('color6', 'Today'))
  contentAdd(columnAddPreview('color7', 'Next'))
  await readPreferences().then(function (data) { refresh() })
  const fragment = window.location.hash.substr(1)
  if (fragment) { document.getElementById(fragment).click(); document.body.scrollTop = 0 }
}
window.onfocus = refresh
