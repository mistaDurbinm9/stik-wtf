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

// ---- home-page chat teaser: one fetch, no polling, doesn't count as presence ----
(function () {
  var teaser = document.getElementById('chat-teaser');
  if (!teaser) return;
  fetch('/api/chat')
    .then(function (r) { if (!r.ok) throw 0; return r.json(); })
    .then(function (j) {
      var badge = document.getElementById('teaser-online');
      if (j.online > 0) {
        badge.textContent = j.online + ' HERE NOW';
        badge.className = 'badge badge-live';
      }
      var msgs = j.msgs || [];
      if (msgs.length) {
        var last = msgs[msgs.length - 1];
        var line = document.getElementById('teaser-line');
        line.textContent = last.name + ': ' + (last.msg.length > 70 ? last.msg.slice(0, 70) + '…' : last.msg);
      }
    })
    .catch(function () {});
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

// ---- ask the little robot ----
(function () {
  var form = document.getElementById('ask-form');
  if (!form) return;
  var out = document.getElementById('ask-answer');
  var status = document.getElementById('ask-status');
  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    var q = document.getElementById('ask-q').value.trim();
    if (q.length < 3) return;
    status.textContent = 'thinking… (a few seconds, it is an old CPU)';
    out.hidden = true;
    fetch('/api/ask', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ q: q })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) { status.textContent = res.j.err || 'it could not answer.'; return; }
        status.textContent = '';
        out.textContent = '';
        var p = document.createElement('p');
        p.textContent = res.j.answer;            // model output: text only, never HTML
        out.appendChild(p);
        if ((res.j.sources || []).length) {
          var s = document.createElement('p');
          s.className = 'ask-sources';
          s.appendChild(document.createTextNode('read: '));
          res.j.sources.forEach(function (src, i) {
            if (i) s.appendChild(document.createTextNode(', '));
            var a = document.createElement('a');
            a.href = src.url;
            a.textContent = src.title;
            s.appendChild(a);
          });
          out.appendChild(s);
        }
        out.hidden = false;
      })
      .catch(function () { status.textContent = 'it could not answer.'; });
  });
})();

// ---- status page: services, visits sparkline, git log ----
(function () {
  var wrap = document.getElementById('svc-cards');
  if (!wrap) return;

  function sparkline(series) {
    var host = document.getElementById('hits-chart');
    host.textContent = '';
    if (!series.length) { host.textContent = ''; return; }
    var vals = series.map(function (s) { return s.visits; });
    var max = Math.max.apply(null, vals) || 1;
    var w = 600, h = 90, gap = 2;
    var bw = Math.max(3, Math.floor(w / series.length) - gap);
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'daily visits, ' + series.length + ' days');
    series.forEach(function (s, i) {
      var bh = Math.max(2, Math.round(s.visits / max * (h - 16)));
      var r = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      r.setAttribute('x', i * (bw + gap));
      r.setAttribute('y', h - bh);
      r.setAttribute('width', bw);
      r.setAttribute('height', bh);
      r.setAttribute('fill', 'var(--accent)');
      var t = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      t.textContent = s.day + ': ' + s.visits + ' visits';
      r.appendChild(t);
      svg.appendChild(r);
    });
    host.appendChild(svg);
  }

  fetch('/api/status')
    .then(function (r) { if (!r.ok) throw 0; return r.json(); })
    .then(function (j) {
      var loading = document.getElementById('svc-loading');
      if (loading) loading.remove();
      (j.services || []).forEach(function (s) {
        var a = document.createElement('a');
        a.className = 'card';
        a.href = s.url;
        var top = document.createElement('div');
        top.className = 'card-top';
        var h3 = document.createElement('h3');
        h3.textContent = s.name;
        var b = document.createElement('span');
        b.className = 'badge ' + (s.up ? 'badge-live' : 'badge-offline');
        b.textContent = s.up ? 'UP' : 'DOWN';
        top.appendChild(h3); top.appendChild(b);
        a.appendChild(top);
        wrap.appendChild(a);
      });

      var series = j.hits || [];
      sparkline(series);
      var total = series.reduce(function (n, s) { return n + s.visits; }, 0);
      document.getElementById('hits-total').textContent = total + ' TOTAL';
      if (series.length < 2) document.getElementById('hits-note').textContent =
        'one day of data so far — the shape shows up after a few days.';
      else document.getElementById('hits-note').textContent = series.length + ' days recorded.';

      var ul = document.getElementById('changes');
      (j.changes || []).forEach(function (c) {
        var li = document.createElement('li');
        li.className = 'update';
        var d = document.createElement('span');
        d.className = 'update-date';
        d.textContent = c.date;
        var body = document.createElement('div');
        body.className = 'update-body';
        var s = document.createElement('strong');
        s.textContent = c.subject;
        var sha = document.createElement('div');
        sha.className = 'update-text';
        sha.textContent = c.sha;
        body.appendChild(s); body.appendChild(sha);
        li.appendChild(d); li.appendChild(body);
        ul.appendChild(li);
      });
    })
    .catch(function () {
      var loading = document.getElementById('svc-loading');
      if (loading) loading.textContent = 'the status endpoint is unreachable.';
    });
})();

// ---- the shared pixel canvas ----
(function () {
  var cv = document.getElementById('cv');
  if (!cv) return;
  var ctx = cv.getContext('2d');
  var status = document.getElementById('cv-status');
  var placedBadge = document.getElementById('cv-placed');
  var palEl = document.getElementById('cv-palette');
  var palette = [], colour = 3, wait = 0, W = 64, H = 64;

  function draw(grid) {
    var img = ctx.createImageData(W, H);
    for (var i = 0; i < W * H; i++) {
      var ch = grid[i];
      var hex = ch === '.' ? null : palette[ch.charCodeAt(0) - 97];
      var r = 255, g = 255, b = 255, a = 0;
      if (hex) {
        r = parseInt(hex.slice(1, 3), 16); g = parseInt(hex.slice(3, 5), 16);
        b = parseInt(hex.slice(5, 7), 16); a = 255;
      }
      img.data[i * 4] = r; img.data[i * 4 + 1] = g; img.data[i * 4 + 2] = b; img.data[i * 4 + 3] = a;
    }
    ctx.putImageData(img, 0, 0);
  }

  function buildPalette() {
    palette.forEach(function (hex, idx) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'cv-swatch' + (idx === colour ? ' active' : '');
      b.style.background = hex;
      b.setAttribute('role', 'radio');
      b.setAttribute('aria-label', 'colour ' + (idx + 1));
      b.setAttribute('aria-checked', idx === colour ? 'true' : 'false');
      b.addEventListener('click', function () {
        colour = idx;
        [].forEach.call(palEl.children, function (c, i) {
          c.classList.toggle('active', i === idx);
          c.setAttribute('aria-checked', i === idx ? 'true' : 'false');
        });
      });
      palEl.appendChild(b);
    });
  }

  function tick() {
    if (wait > 0) {
      wait--;
      status.textContent = wait > 0 ? 'next pixel in ' + wait + 's' : 'your turn — click a pixel.';
    }
  }
  setInterval(tick, 1000);

  function apply(j) {
    palette = j.palette;
    if (!palEl.children.length) buildPalette();
    draw(j.grid);
    placedBadge.textContent = j.placed + (j.placed === 1 ? ' PIXEL' : ' PIXELS');
    if (typeof j.wait === 'number') wait = j.wait;
  }

  function load() {
    fetch('/api/canvas').then(function (r) { return r.json(); }).then(apply)
      .catch(function () { status.textContent = 'the board is unreachable right now.'; });
  }
  load();
  setInterval(function () { if (!document.hidden) load(); }, 8000);

  cv.addEventListener('click', function (ev) {
    var r = cv.getBoundingClientRect();
    var x = Math.floor((ev.clientX - r.left) / r.width * W);
    var y = Math.floor((ev.clientY - r.top) / r.height * H);
    if (x < 0 || y < 0 || x >= W || y >= H) return;
    if (wait > 0) { status.textContent = 'still cooling down — ' + wait + 's'; return; }
    status.textContent = 'placing…';
    fetch('/api/canvas', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ x: x, y: y, c: colour })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (res.ok) { apply(res.j); status.textContent = 'placed at ' + x + ',' + y + '.'; }
        else { wait = res.j.wait || 0; status.textContent = res.j.err || 'that did not place.'; }
      })
      .catch(function () { status.textContent = 'that did not place.'; });
  });
})();

// ---- whitelist application form ----
(function () {
  var form = document.getElementById('apply-form');
  if (!form) return;
  var status = document.getElementById('apply-status');
  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    var val = function (id) { return (document.getElementById(id) || {}).value || ''; };
    status.textContent = 'sending…';
    fetch('/api/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mcname: val('ap-mcname'), platform: val('ap-platform'), discord: val('ap-discord'),
        age: val('ap-age'), found: val('ap-found'), why: val('ap-why'),
        experience: val('ap-exp'), website: val('ap-website')
      })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (res.ok && res.j.ok) {
          form.hidden = true;
          document.getElementById('apply-done').hidden = false;
        } else {
          status.textContent = res.j.err || 'that did not send.';
        }
      })
      .catch(function () { status.textContent = 'that did not send — try again in a minute.'; });
  });
})();

// ---- application review (opened from the emailed capability link) ----
(function () {
  var card = document.getElementById('rev-card');
  if (!card) return;
  var qs = new URLSearchParams(location.search);
  var id = qs.get('id'), tok = qs.get('t');
  var intro = document.getElementById('rev-intro');
  var msg = document.getElementById('rev-status-msg');
  if (!id || !tok) { intro.textContent = 'This page needs the link from the notification email.'; return; }

  var LABELS = { platform: 'platform', discord: 'discord', age: 'age', found: 'found via',
                 why: 'why they want in', experience: 'what they build' };

  function paint(a) {
    intro.hidden = true;
    card.hidden = false;
    document.getElementById('rev-name').textContent = a.mcname;
    var badge = document.getElementById('rev-status');
    badge.textContent = (a.status || 'new').toUpperCase();
    badge.className = 'badge' + (a.status === 'approved' ? ' badge-live' : a.status === 'denied' ? ' badge-offline' : '');
    var ul = document.getElementById('rev-fields');
    ul.textContent = '';
    Object.keys(LABELS).forEach(function (k) {
      if (!a[k]) return;
      var li = document.createElement('li');
      var b = document.createElement('strong');
      b.textContent = LABELS[k] + ': ';
      var s = document.createElement('span');
      s.textContent = a[k];           // untrusted input: textContent only
      li.appendChild(b); li.appendChild(s); ul.appendChild(li);
    });
    var when = document.createElement('li');
    when.className = 'update-date';
    when.textContent = 'submitted ' + new Date(a.t * 1000).toLocaleString();
    ul.appendChild(when);
    if (a.status === 'approved') showCmd(a.mcname);
    if (a.note) { msg.textContent = 'note: ' + a.note; }
  }

  function showCmd(name) {
    document.getElementById('rev-cmd').textContent = 'whitelist add ' + name;
    document.getElementById('rev-next').hidden = false;
  }

  function decide(decision) {
    msg.textContent = 'saving…';
    fetch('/api/apply/decide', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: id, t: tok, decision: decision, note: document.getElementById('rev-note').value })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) { msg.textContent = res.j.err || 'that did not save.'; return; }
        var badge = document.getElementById('rev-status');
        badge.textContent = res.j.status.toUpperCase();
        badge.className = 'badge' + (res.j.status === 'approved' ? ' badge-live' : ' badge-offline');
        msg.textContent = 'saved.';
        if (res.j.status === 'approved') showCmd(res.j.mcname);
        else document.getElementById('rev-next').hidden = true;
      })
      .catch(function () { msg.textContent = 'that did not save.'; });
  }

  fetch('/api/apply/get?id=' + encodeURIComponent(id) + '&t=' + encodeURIComponent(tok))
    .then(function (r) { if (!r.ok) throw 0; return r.json(); })
    .then(paint)
    .catch(function () { intro.textContent = 'That application could not be found — the link may be wrong or very old.'; });

  document.getElementById('rev-approve').addEventListener('click', function () { decide('approve'); });
  document.getElementById('rev-deny').addEventListener('click', function () { decide('deny'); });
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

        // power rides along on the same response — no extra request
        var pw = document.getElementById('power');
        var p = j.power;
        if (pw && p && p.watts > 0) {
          var order = Object.keys(p.sources).sort(function (a, b) {
            return (a === 'node' ? -1 : b === 'node' ? 1 : a.localeCompare(b));
          });
          var parts = order.map(function (k) { return k + ' ' + Math.round(p.sources[k].watts); });
          // sits inline with uptime, so: headline total, breakdown only when there's more
          // than one machine awake, and the per-chip detail stays in the tooltip.
          var line = Math.round(p.watts) + 'W';
          if (parts.length > 1) line += ' (' + parts.join(' + ') + ')';
          else if (order.length === 1) line = order[0] + ' ' + line;
          // energy is one quantity, shown in whatever unit keeps it readable:
          // watt-hours until there's a kilowatt-hour, then kWh, then MWh.
          var wh = p.kwh * 1000;
          var energy = wh >= 1e6 ? (p.kwh / 1000).toFixed(2) + ' MWh'
                     : wh >= 1000 ? p.kwh.toFixed(p.kwh >= 10 ? 1 : 2) + ' kWh'
                     : Math.round(wh) + ' Wh';
          if (wh >= 1) line += ' · ' + energy + ' since ' +
            new Date(p.since * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
          pw.textContent = ' · ' + line;
          pw.hidden = false;
        }
      })
      .catch(function () {});
  }
})();
