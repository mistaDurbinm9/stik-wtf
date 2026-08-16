// stik.wtf interactivity. Rules: sprites move in steps(), nothing tweens.

// ---- pixel burst on click: 6 pixels on buttons, 3 anywhere else ----
document.addEventListener('pointerdown', function (e) {
  var btn = e.target.closest('.btn, .mc-copy');
  var n = btn ? 6 : 3;
  for (var i = 0; i < n; i++) {
    var p = document.createElement('span');
    p.className = 'pix';
    var a = (Math.PI * 2 * i) / n + Math.random();
    p.style.left = e.clientX + 'px';
    p.style.top = e.clientY + 'px';
    p.style.setProperty('--dx', Math.round(Math.cos(a) * (14 + Math.random() * 14)) + 'px');
    p.style.setProperty('--dy', Math.round(Math.sin(a) * (14 + Math.random() * 14)) + 'px');
    if (i % 2) p.style.background = 'var(--ink)';
    document.body.appendChild(p);
    p.addEventListener('animationend', function () { this.remove(); });
  }
});

// ---- the fish ----
function spawnFish(delay) {
  var tpl = document.getElementById('pix-fish');
  if (!tpl) return;
  setTimeout(function () {
    var f = tpl.content.firstElementChild.cloneNode(true);
    f.classList.add('swimming');
    f.style.top = Math.round(10 + Math.random() * 70) + 'vh';
    f.style.animationDuration = (7 + Math.random() * 6) + 's';
    document.body.appendChild(f);
    f.addEventListener('animationend', function () { f.remove(); });
  }, delay);
}

// ---- the mascot: stik rides the onewheel along the bottom edge ----
function spawnStik(delay) {
  var tpl = document.getElementById('pix-stik');
  if (!tpl) return;
  setTimeout(function () {
    var s = tpl.content.firstElementChild.cloneNode(true);
    s.classList.add('riding');
    s.style.animationDuration = (6 + Math.random() * 5) + 's';
    document.body.appendChild(s);
    s.addEventListener('animationend', function () { s.remove(); });
  }, delay);
}

// occasional ambient ride-by: 1 in 5 page loads
if (Math.random() < 0.2) spawnStik(5000 + Math.random() * 10000);

// typing "wtf" — or tapping the ".wtf" in the wordmark — summons the school
function summonSchool() {
  for (var i = 0; i < 8; i++) spawnFish(i * 350 + Math.random() * 200);
}
var seq = '';
document.addEventListener('keydown', function (e) {
  if (e.target instanceof Element && e.target.closest('input, textarea, select')) return;
  seq = (seq + e.key).slice(-3);
  if (seq === 'wtf') { summonSchool(); seq = ''; }
});
// the touch path: tapping any fish on the site summons the school
document.addEventListener('click', function (e) {
  if (e.target.closest('.fish-egg')) summonSchool();
});

// ---- stik speaks ----
var STIK_LINES = [
  'i host this myself, you know.',
  'zero open ports. count them.',
  'the shadows are load-bearing.',
  'sign the guestbook or the fish gets it.',
  'every pixel of me is hand-placed.',
  '384GB of RAM and i still ride a onewheel.',
  'type wtf. trust me.',
  'the node hums. i listen.'
];
var stikLine = Math.floor(Math.random() * STIK_LINES.length);
document.addEventListener('click', function (e) {
  var s = e.target.closest('.stik-egg, .pix-stik.riding');
  if (!s) return;
  var old = document.querySelector('.stik-bubble');
  if (old) old.remove();
  var r = s.getBoundingClientRect();
  var b = document.createElement('div');
  b.className = 'stik-bubble';
  b.textContent = STIK_LINES[stikLine++ % STIK_LINES.length];
  document.body.appendChild(b);
  b.style.left = Math.max(8, Math.min(r.left, window.innerWidth - b.offsetWidth - 8)) + 'px';
  b.style.top = Math.max(8, r.top - b.offsetHeight - 10) + 'px';
  setTimeout(function () { b.remove(); }, 2600);
});

// ---- live minecraft status ----
var mc = document.querySelector('[data-mc]');
if (mc) {
  var host = mc.getAttribute('data-mc');
  var badge = mc.querySelector('.mc-badge');
  var line = mc.querySelector('.mc-line');

  var render = function (j) {
    if (j && j.online) {
      badge.textContent = 'ONLINE';
      badge.className = 'badge mc-badge badge-live';
      var p = j.players || {};
      var txt = (p.online || 0) + '/' + (p.max || '?') + ' players';
      if (j.version) txt += ' · ' + j.version;
      var names = (p.list || []).map(function (x) { return x.name; }).filter(Boolean);
      if (names.length) txt += ' — ' + names.slice(0, 10).join(', ');
      line.textContent = txt;
    } else {
      badge.textContent = 'OFFLINE';
      badge.className = 'badge mc-badge badge-offline';
      line.textContent = 'nobody home right now.';
    }
  };

  var cached = null;
  try { cached = JSON.parse(sessionStorage.getItem('mc-status') || 'null'); } catch (e) {}
  if (cached && Date.now() - cached.t < 60000) {
    render(cached.j);
  } else {
    fetch('https://api.mcsrvstat.us/3/' + host)
      .then(function (r) { return r.json(); })
      .then(function (j) {
        try { sessionStorage.setItem('mc-status', JSON.stringify({ t: Date.now(), j: j })); } catch (e) {}
        render(j);
      })
      .catch(function () {
        badge.textContent = 'UNKNOWN';
        badge.className = 'badge mc-badge';
        line.textContent = "status check didn't answer — the server may still be up; try joining.";
      });
  }

  var copy = mc.querySelector('.mc-copy');
  if (copy) copy.addEventListener('click', function () {
    navigator.clipboard.writeText(host).then(function () {
      copy.textContent = 'COPIED ✓';
      setTimeout(function () { copy.textContent = 'COPY IP'; }, 1200);
    });
  });
}

// ---- snippet copy buttons (the wall) ----
document.addEventListener('click', function (e) {
  var b = e.target.closest('.copy-snip');
  if (!b) return;
  var t = document.getElementById(b.getAttribute('data-copy-target'));
  if (!t) return;
  navigator.clipboard.writeText(t.textContent).then(function () {
    b.textContent = 'COPIED ✓';
    setTimeout(function () { b.textContent = 'COPY'; }, 1200);
  });
});

// ---- guestbook ----
(function () {
  var form = document.getElementById('gb-form');
  if (!form) return;
  var list = document.getElementById('gb-entries');
  var empty = document.getElementById('gb-empty');
  var status = document.getElementById('gb-status');

  function row(e) {
    var li = document.createElement('li');
    li.className = 'update';
    var date = document.createElement('span');
    date.className = 'update-date';
    date.textContent = new Date(e.t * 1000).toISOString().slice(0, 10);
    var body = document.createElement('div');
    body.className = 'update-body';
    var name = document.createElement('strong');
    name.textContent = e.name; // textContent everywhere: entries are untrusted
    var msg = document.createElement('div');
    msg.className = 'update-text';
    msg.textContent = e.msg;
    body.appendChild(name);
    body.appendChild(msg);
    li.appendChild(date);
    li.appendChild(body);
    return li;
  }

  fetch('/api/guestbook')
    .then(function (r) { if (!r.ok) throw 0; return r.json(); })
    .then(function (j) {
      var entries = (j.entries || []).reverse(); // newest first
      entries.forEach(function (e) { list.appendChild(row(e)); });
      empty.hidden = entries.length > 0;
    })
    .catch(function () { status.textContent = 'the book is unreachable right now.'; });

  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    status.textContent = 'signing…';
    fetch('/api/guestbook', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: document.getElementById('gb-name').value,
        msg: document.getElementById('gb-msg').value,
        website: document.getElementById('gb-website').value
      })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (res.ok && res.j.entry) {
          list.insertBefore(row(res.j.entry), list.firstChild);
          empty.hidden = true;
          form.reset();
          status.textContent = 'signed. ✓';
        } else {
          status.textContent = res.j.err || 'that did not work.';
        }
      })
      .catch(function () { status.textContent = 'that did not work.'; });
  });
})();

// ---- the shoutbox: poll while visible, 5s cadence ----
(function () {
  var box = document.getElementById('chat-box');
  if (!box) return;
  var list = document.getElementById('chat-msgs');
  var online = document.getElementById('chat-online');
  var empty = document.getElementById('chat-empty');
  var status = document.getElementById('chat-status');
  var nameInput = document.getElementById('chat-name');
  var since = 0;
  nameInput.value = localStorage.getItem('chat-name') || '';

  function row(m) {
    var li = document.createElement('li');
    var time = document.createElement('span');
    time.className = 'chat-time';
    var d = new Date(m.t * 1000);
    time.textContent = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
    var name = document.createElement('strong');
    name.textContent = m.name; // untrusted: textContent only
    if (m.name === 'stik') name.className = 'chat-owner';
    var msg = document.createElement('span');
    msg.textContent = m.msg;
    li.appendChild(time);
    li.appendChild(name);
    li.appendChild(msg);
    return li;
  }

  function poll() {
    fetch('/api/chat?since=' + since)
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (j) {
        online.textContent = j.online + ' HERE';
        (j.msgs || []).forEach(function (m) {
          list.appendChild(row(m));
          since = Math.max(since, m.t);
        });
        while (list.children.length > 100) list.removeChild(list.firstChild);
        empty.hidden = list.children.length > 0;
        list.scrollTop = list.scrollHeight;
      })
      .catch(function () { online.textContent = 'OFFLINE'; });
  }

  poll();
  setInterval(function () { if (!document.hidden) poll(); }, 5000);

  document.getElementById('chat-form').addEventListener('submit', function (ev) {
    ev.preventDefault();
    var msgInput = document.getElementById('chat-msg');
    try { localStorage.setItem('chat-name', nameInput.value); } catch (e) {}
    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: nameInput.value,
        msg: msgInput.value,
        website: document.getElementById('chat-website').value
      })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (res.ok && res.j.msg) {
          msgInput.value = '';
          status.textContent = '';
          poll();
        } else {
          status.textContent = res.j.err || 'that did not work.';
        }
      })
      .catch(function () { status.textContent = 'that did not work.'; });
  });
})();

// ---- hit counter + uptime (lights up once the node endpoints exist) ----
(function () {
  var hits = document.getElementById('hits');
  var up = document.getElementById('uptime');
  if (hits) {
    var peek = sessionStorage.getItem('counted') ? '?peek=1' : '';
    fetch('/api/count' + peek)
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (j) {
        try { sessionStorage.setItem('counted', '1'); } catch (e) {}
        hits.textContent = 'you are visitor #' + String(j.n).padStart(6, '0');
        hits.hidden = false;
      })
      .catch(function () {}); // no endpoint (dev / pre-deploy): stay hidden
  }
  if (up) {
    fetch('/api/uptime')
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (j) {
        var s = j.seconds != null ? j.seconds : j.days * 86400;
        var pad = function (n) { return String(n).padStart(2, '0'); };
        var render = function () {
          var rest = s % 86400;
          up.textContent = ' · node up ' + Math.floor(s / 86400) + 'd ' +
            pad(Math.floor(rest / 3600)) + ':' + pad(Math.floor((rest % 3600) / 60)) + ':' + pad(rest % 60);
        };
        render();
        up.hidden = false;
        setInterval(function () { s++; render(); }, 1000); // ticks locally; one fetch total
      })
      .catch(function () {});
  }
})();
