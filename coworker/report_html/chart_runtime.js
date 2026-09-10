/**
 * ChemClaw report HTML chart runtime — GUI-aligned candlestick/line charts
 * with left detail rail, crosshair, click-to-pin, and X zoom/pan.
 */
(function () {
  "use strict";

  var BOOT = window.CHEMCLAW_CHART_BOOT || {};
  var SPECS = BOOT.specs || [];
  var COLORS = BOOT.colors || ["#2563eb", "#D55E00", "#009E73", "#CC79A7"];
  var UP = BOOT.up || "#ef4444";
  var DOWN = BOOT.down || "#22c55e";
  var UP_W = BOOT.upWick || "#dc2626";
  var DOWN_W = BOOT.downWick || "#16a34a";
  var AXIS_RAIL = 188;
  var DEFAULT_WINDOW = 90;
  var MOBILE_WINDOW = 24;

  if (typeof Chart === "undefined" || !SPECS.length) return;

  if (typeof ChartZoom !== "undefined") {
    Chart.register(ChartZoom);
  } else if (window["chartjs-plugin-zoom"]) {
    Chart.register(window["chartjs-plugin-zoom"]);
  }
  if (window["chartjs-plugin-annotation"]) {
    Chart.register(window["chartjs-plugin-annotation"]);
  }

  var crosshairPlugin = {
    id: "chemclawAxisCrosshair",
    afterDraw: function (chart) {
      var idx = chart.$hoverIndex;
      if (idx == null || !isFinite(idx)) return;
      var index = Math.round(idx);
      var area = chart.chartArea;
      if (!area) return;
      var meta0 = chart.getDatasetMeta(0);
      var el0 = meta0 && meta0.data && meta0.data[index];
      if (!el0 || !isFinite(el0.x)) return;
      var x = el0.x;
      var ctx = chart.ctx;
      var datasets = chart.data.datasets || [];
      var yScale = chart.scales.y;
      var y;
      if (datasets.length === 1 && yScale) {
        var raw = datasets[0].data && datasets[0].data[index];
        var value;
        if (typeof raw === "number" && isFinite(raw)) value = raw;
        else if (raw && typeof raw === "object") {
          if (typeof raw.c === "number" && isFinite(raw.c)) value = raw.c;
          else if (typeof raw.y === "number" && isFinite(raw.y)) value = raw.y;
        }
        if (value != null) y = yScale.getPixelForValue(value);
        else if (isFinite(el0.y)) y = el0.y;
      }
      ctx.save();
      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = "rgba(15, 23, 42, 0.28)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, area.top);
      ctx.lineTo(x, area.bottom);
      ctx.stroke();
      if (y != null && isFinite(y)) {
        ctx.beginPath();
        ctx.moveTo(area.left, y);
        ctx.lineTo(area.right, y);
        ctx.stroke();
      }
      ctx.restore();
    },
  };
  Chart.register(crosshairPlugin);

  function isMobile() {
    return window.matchMedia && window.matchMedia("(max-width: 640px)").matches;
  }

  function formatPrice(v) {
    if (v == null || !isFinite(v)) return "—";
    return Number(v).toLocaleString("zh-CN", { maximumFractionDigits: 2 });
  }

  function defaultXWindow(count, size) {
    if (count <= 0) return { min: 0, max: 0 };
    var max = count - 1;
    var min = Math.max(0, count - size);
    return { min: min, max: max };
  }

  function yRangeForVisibleBars(ohlc, xMin, xMax) {
    if (!ohlc.length) return null;
    var lo = Math.max(0, Math.floor(Math.min(xMin, xMax)));
    var hi = Math.min(ohlc.length - 1, Math.ceil(Math.max(xMin, xMax)));
    var yMin = Infinity;
    var yMax = -Infinity;
    for (var i = lo; i <= hi; i++) {
      var bar = ohlc[i];
      if (!bar) continue;
      if (bar.l < yMin) yMin = bar.l;
      if (bar.h > yMax) yMax = bar.h;
    }
    if (!isFinite(yMin) || !isFinite(yMax)) return null;
    var span = Math.max(yMax - yMin, Math.abs(yMax) * 0.01, 1e-6);
    var pad = span * 0.12;
    return { min: yMin - pad, max: yMax + pad };
  }

  function yRangeForVisibleSeries(values, xMin, xMax) {
    var lo = Math.max(0, Math.floor(Math.min(xMin, xMax)));
    var hi = Math.min(values.length - 1, Math.ceil(Math.max(xMin, xMax)));
    var yMin = Infinity;
    var yMax = -Infinity;
    for (var i = lo; i <= hi; i++) {
      var v = values[i];
      if (typeof v !== "number" || !isFinite(v)) continue;
      if (v < yMin) yMin = v;
      if (v > yMax) yMax = v;
    }
    if (!isFinite(yMin) || !isFinite(yMax)) return null;
    var span = Math.max(yMax - yMin, Math.abs(yMax) * 0.01, 1e-6);
    var pad = span * 0.12;
    return { min: yMin - pad, max: yMax + pad };
  }

  function fitYToVisibleBars(chart, ohlc) {
    var xScale = chart.scales.x;
    var yScale = chart.scales.y;
    if (!xScale || !yScale) return;
    var range = yRangeForVisibleBars(ohlc, xScale.min, xScale.max);
    if (!range) return;
    yScale.options.min = range.min;
    yScale.options.max = range.max;
    chart.update("none");
  }

  function fitYToVisibleSeries(chart, seriesList) {
    var xScale = chart.scales.x;
    var yScale = chart.scales.y;
    if (!xScale || !yScale) return;
    var yMin = Infinity;
    var yMax = -Infinity;
    seriesList.forEach(function (values) {
      var range = yRangeForVisibleSeries(values, xScale.min, xScale.max);
      if (!range) return;
      yMin = Math.min(yMin, range.min);
      yMax = Math.max(yMax, range.max);
    });
    if (!isFinite(yMin) || !isFinite(yMax)) return;
    var span = Math.max(yMax - yMin, Math.abs(yMax) * 0.01, 1e-6);
    var pad = span * 0.12;
    yScale.options.min = yMin - pad;
    yScale.options.max = yMax + pad;
    chart.update("none");
  }

  var STAGE_TONE_COLORS = {
    up: { band: "rgba(229, 57, 53, 0.12)" },
    down: { band: "rgba(27, 158, 90, 0.12)" },
    side: { band: "rgba(37, 99, 235, 0.10)" },
  };
  var SIDE_ABS_FLOOR = 0.008;
  var SIDE_REL_RATIO = 0.4;

  function findLabelIndex(labels, needle) {
    var n = String(needle || "").trim();
    if (!n) return -1;
    for (var i = 0; i < labels.length; i++) {
      if (labels[i] === n) return i;
    }
    for (var j = 0; j < labels.length; j++) {
      var l = labels[j];
      if (l.endsWith(n) || n.endsWith(l)) return j;
    }
    for (var k = 0; k < labels.length; k++) {
      var label = labels[k];
      if (label.indexOf(n) >= 0 || n.indexOf(label) >= 0) return k;
    }
    return -1;
  }

  function resolveChartStages(labels, stages) {
    if (!stages || !stages.length) return [];
    var out = [];
    stages.forEach(function (stage) {
      if (!stage) return;
      var startIndex = findLabelIndex(labels, stage.start);
      var endIndex = findLabelIndex(labels, stage.end);
      if (startIndex < 0 || endIndex < 0) return;
      if (startIndex > endIndex) {
        var tmp = startIndex;
        startIndex = endIndex;
        endIndex = tmp;
      }
      out.push({
        start: stage.start,
        end: stage.end,
        tone: stage.tone || "side",
        reason: stage.reason || "",
        startIndex: startIndex,
        endIndex: endIndex,
      });
    });
    return out;
  }

  function exclusiveStageRanges(stages) {
    if (!stages.length) return [];
    var maxIndex = 0;
    stages.forEach(function (stage) {
      if (stage.endIndex > maxIndex) maxIndex = stage.endIndex;
    });
    var owner = new Array(maxIndex + 1);
    for (var i = 0; i <= maxIndex; i++) owner[i] = null;
    stages.forEach(function (stage) {
      for (var j = Math.max(0, stage.startIndex); j <= stage.endIndex; j++) {
        owner[j] = stage;
      }
    });
    var out = [];
    var runStart = -1;
    var runStage = null;
    function flush(end) {
      if (runStage && runStart >= 0) {
        out.push({
          start: runStage.start,
          end: runStage.end,
          tone: runStage.tone,
          reason: runStage.reason,
          startIndex: runStart,
          endIndex: end,
        });
      }
    }
    for (var x = 0; x <= maxIndex; x++) {
      var cur = owner[x];
      if (cur !== runStage) {
        if (runStage) flush(x - 1);
        runStart = cur ? x : -1;
        runStage = cur;
      }
    }
    if (runStage) flush(maxIndex);
    return out;
  }

  function stageReturnPct(startPx, endPx) {
    if (typeof startPx !== "number" || typeof endPx !== "number") return null;
    if (!isFinite(startPx) || !isFinite(endPx) || startPx === 0) return null;
    return (endPx - startPx) / startPx;
  }

  function classifyStageTones(returns) {
    var abs = returns.map(function (r) {
      return r == null ? 0 : Math.abs(r);
    });
    var rmax = abs.reduce(function (m, v) {
      return v > m ? v : m;
    }, 0);
    if (rmax < SIDE_ABS_FLOOR) return returns.map(function () {
      return "side";
    });
    var sideMax = SIDE_REL_RATIO * rmax;
    return returns.map(function (r) {
      if (r == null || Math.abs(r) < sideMax) return "side";
      return r > 0 ? "up" : "down";
    });
  }

  function overlayComputedStageTones(stages, priceAt) {
    if (!stages.length) return stages;
    var returns = stages.map(function (s) {
      return stageReturnPct(priceAt(s.startIndex), priceAt(s.endIndex));
    });
    var tones = classifyStageTones(returns);
    return stages.map(function (s, i) {
      return {
        start: s.start,
        end: s.end,
        tone: tones[i] || "side",
        reason: s.reason,
        startIndex: s.startIndex,
        endIndex: s.endIndex,
      };
    });
  }

  function paintStageBands(resolved) {
    var annotations = {};
    for (var si = 0; si < resolved.length; si++) {
      var stage = resolved[si];
      var paint = STAGE_TONE_COLORS[stage.tone] || STAGE_TONE_COLORS.side;
      annotations["stageBand" + si] = {
        type: "box",
        xMin: stage.startIndex - 0.5,
        xMax: stage.endIndex + 0.5,
        backgroundColor: paint.band,
        borderWidth: 0,
        drawTime: "beforeDatasetsDraw",
      };
    }
    return annotations;
  }

  function resolvedStagesForSpec(spec) {
    var labels = spec.labels || [];
    var stages = resolveChartStages(labels, spec.stages);
    if (!stages.length) return [];
    if (spec.type === "candlestick") {
      var ohlc = spec.ohlc || [];
      return exclusiveStageRanges(
        overlayComputedStageTones(stages, function (i) {
          var bar = ohlc[i];
          return bar ? bar.c : null;
        })
      );
    }
    var values = ((spec.series || [])[0] || {}).values || [];
    return exclusiveStageRanges(
      overlayComputedStageTones(stages, function (i) {
        var v = values[i];
        return typeof v === "number" && isFinite(v) ? v : null;
      })
    );
  }

  function buildStageAnnotations(spec) {
    var resolved = resolvedStagesForSpec(spec);
    return resolved.length ? paintStageBands(resolved) : {};
  }

  function findStageAtIndex(stages, index) {
    if (!isFinite(index)) return null;
    var i = Math.round(index);
    var found = null;
    for (var s = 0; s < stages.length; s++) {
      var stage = stages[s];
      if (i >= stage.startIndex && i <= stage.endIndex) found = stage;
    }
    return found;
  }

  function toneLabel(tone) {
    if (tone === "up") return "上涨";
    if (tone === "down") return "下跌";
    return "横盘";
  }

  function updateCrosshairStatus(chartId, pinned) {
    var status = document.getElementById(chartId + "-status");
    if (!status) return;
    status.textContent = pinned ? "十字线已固定" : "十字线跟随鼠标";
    status.setAttribute("data-pinned", pinned ? "true" : "false");
  }

  function updatePanel(panel, spec, index, pinned) {
    if (!panel) return;
    var labels = spec.labels || [];
    var dateEl = panel.querySelector('[data-role="date"]');
    var ohlcEl = panel.querySelector('[data-role="ohlc"]');
    var seriesEl = panel.querySelector('[data-role="series"]');
    var stageEl = panel.querySelector('[data-role="stage"]');
    if (dateEl) dateEl.textContent = labels[index] || "";
    panel.hidden = false;
    panel.setAttribute("aria-hidden", "false");
    if (pinned) panel.classList.add("chart-axis-panel--pinned");
    else panel.classList.remove("chart-axis-panel--pinned");

    if (ohlcEl) ohlcEl.innerHTML = "";
    if (seriesEl) seriesEl.innerHTML = "";
    if (stageEl) stageEl.innerHTML = "";

    if (spec.type === "candlestick" && ohlcEl) {
      var bar = (spec.ohlc || [])[index];
      if (!bar) return;
      var barUp = bar.c >= bar.o;
      var ocColor = barUp ? UP : DOWN;
      ohlcEl.hidden = false;
      if (seriesEl) seriesEl.hidden = true;
      ohlcEl.innerHTML =
        rowKV("开盘", formatPrice(bar.o), ocColor) +
        rowKV("最高", formatPrice(bar.h), UP) +
        rowKV("最低", formatPrice(bar.l), DOWN) +
        rowKV("收盘", formatPrice(bar.c), ocColor);
    } else if (seriesEl) {
      ohlcEl && (ohlcEl.hidden = true);
      seriesEl.hidden = false;
      (spec.series || []).forEach(function (s, i) {
        var val = (s.values || [])[index];
        var color = COLORS[i % COLORS.length];
        seriesEl.innerHTML +=
          '<div class="chart-axis-panel-kv chart-axis-panel-kv--stack">' +
          '<span class="chart-axis-panel-k" style="color:' +
          color +
          '">' +
          escapeHtml(s.name || "系列") +
          "</span>" +
          '<span class="chart-axis-panel-v">' +
          formatPrice(val) +
          (spec.unit ? " " + escapeHtml(spec.unit) : "") +
          "</span></div>";
      });
    }

    var stage = findStageAtIndex(spec.$resolvedStages || [], index);
    if (stage && stageEl) {
      stageEl.hidden = false;
      stageEl.innerHTML =
        '<div class="chart-axis-panel-head">' +
        '<span class="chart-axis-panel-tone" data-tone="' +
        escapeHtml(stage.tone || "side") +
        '"></span>' +
        '<span class="chart-axis-panel-tone-text">' +
        toneLabel(stage.tone) +
        "</span></div>" +
        '<div class="chart-axis-panel-row"><span class="chart-axis-panel-label">区间</span>' +
        '<span class="chart-axis-panel-value">' +
        escapeHtml(stage.start) +
        " – " +
        escapeHtml(stage.end) +
        "</span></div>" +
        (stage.reason
          ? '<div class="chart-axis-panel-row"><span class="chart-axis-panel-label">驱动</span>' +
            '<span class="chart-axis-panel-value chart-axis-panel-reason">' +
            escapeHtml(stage.reason) +
            "</span></div>"
          : "");
    } else if (stageEl) {
      stageEl.hidden = true;
    }
  }

  function rowKV(k, v, color) {
    return (
      '<div class="chart-axis-panel-kv chart-axis-panel-kv--row">' +
      '<span class="chart-axis-panel-k">' +
      k +
      "</span>" +
      '<span class="chart-axis-panel-v" style="color:' +
      color +
      '">' +
      v +
      "</span></div>"
    );
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function indexFromClient(chart, canvas, spec, clientX, clientY) {
    var xScale = chart.scales.x;
    if (!xScale) return null;
    var rect = canvas.getBoundingClientRect();
    var px = clientX - rect.left;
    var py = clientY - rect.top;
    var area = chart.chartArea;
    if (area && (px < area.left || px > area.right || py < area.top || py > area.bottom)) {
      return null;
    }
    var dataX = Number(xScale.getValueForPixel(px));
    if (!isFinite(dataX)) return null;
    var index = Math.round(dataX);
    var max = Math.max(0, (spec.labels || []).length - 1);
    if (index < 0 || index > max) return null;
    return index;
  }

  function buildCandleConfig(spec) {
    var bars = spec.ohlc || [];
    var labels = spec.labels || [];
    var win = defaultXWindow(bars.length, DEFAULT_WINDOW);
    var yWin = yRangeForVisibleBars(bars, win.min, win.max);
    var xMax = Math.max(0, bars.length - 1);
    var stageAnnotations = buildStageAnnotations(spec);
    var zoomOpts = {
      limits: { x: { min: 0, max: xMax, minRange: Math.min(5, Math.max(1, bars.length)) } },
      pan: {
        enabled: true,
        mode: "x",
        onPanComplete: function (ctx) {
          fitYToVisibleBars(ctx.chart, bars);
        },
      },
      zoom: {
        wheel: { enabled: true },
        pinch: { enabled: true },
        mode: "x",
        onZoomComplete: function (ctx) {
          fitYToVisibleBars(ctx.chart, bars);
        },
      },
    };
    return {
      type: "candlestick",
      data: {
        datasets: [
          {
            label: spec.title || "OHLC",
            data: bars.map(function (bar, i) {
              return { x: i, o: bar.o, h: bar.h, l: bar.l, c: bar.c };
            }),
            borderColors: { up: DOWN_W, down: UP_W, unchanged: "#94a3b8" },
            backgroundColors: { up: DOWN, down: UP, unchanged: "#94a3b8" },
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { left: AXIS_RAIL, top: 32, right: 36, bottom: 20 } },
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: false },
          title: {
            display: !!spec.title,
            text: spec.title || "",
            color: "#1f2937",
            font: { size: 13, weight: "600" },
          },
          tooltip: { enabled: false },
          zoom: zoomOpts,
          annotation: { annotations: stageAnnotations },
        },
        scales: {
          x: {
            type: "linear",
            offset: false,
            min: win.min,
            max: win.max,
            grid: { color: "rgba(15,23,42,0.06)" },
            ticks: {
              color: "#64748b",
              autoSkip: true,
              maxTicksLimit: isMobile() ? 6 : 8,
              callback: function (value) {
                var i = Math.round(Number(value));
                return labels[i] || "";
              },
            },
          },
          y: {
            beginAtZero: false,
            min: yWin ? yWin.min : undefined,
            max: yWin ? yWin.max : undefined,
            grid: { color: "rgba(15,23,42,0.06)" },
            ticks: { color: "#64748b" },
          },
        },
      },
    };
  }

  function buildSeriesConfig(spec) {
    var labels = spec.labels || [];
    var win = defaultXWindow(labels.length, DEFAULT_WINDOW);
    var seriesList = (spec.series || []).map(function (s) {
      return s.values || [];
    });
    var stageAnnotations = buildStageAnnotations(spec);
    var yWin =
      seriesList.length === 1
        ? yRangeForVisibleSeries(seriesList[0], win.min, win.max)
        : null;
    var chartType = spec.type === "area" ? "line" : spec.type || "line";
    var xMax = Math.max(0, labels.length - 1);
    var datasets = (spec.series || []).map(function (s, i) {
      var color = COLORS[i % COLORS.length];
      return {
        label: s.name,
        data: s.values,
        borderColor: color,
        backgroundColor: spec.type === "area" ? color + "33" : color,
        fill: spec.type === "area",
        tension: 0.25,
        pointRadius: labels.length > 24 ? 0 : 2,
        pointHoverRadius: 4,
      };
    });
    return {
      type: chartType,
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { left: AXIS_RAIL, top: 16, right: 24, bottom: 16 } },
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: spec.showLegend !== false, labels: { color: "#1f2937" } },
          title: {
            display: !!spec.title,
            text: spec.title || "",
            color: "#1f2937",
            font: { size: 13, weight: "600" },
          },
          tooltip: { enabled: false },
          zoom: {
            limits: { x: { min: 0, max: xMax, minRange: Math.min(5, Math.max(1, labels.length)) } },
            pan: {
              enabled: true,
              mode: "x",
              onPanComplete: function (ctx) {
                fitYToVisibleSeries(ctx.chart, seriesList);
              },
            },
            zoom: {
              wheel: { enabled: true },
              pinch: { enabled: true },
              mode: "x",
              onZoomComplete: function (ctx) {
                fitYToVisibleSeries(ctx.chart, seriesList);
              },
            },
          },
          annotation: { annotations: stageAnnotations },
        },
        scales: {
          x: {
            min: win.min,
            max: win.max,
            grid: { color: "rgba(15,23,42,0.06)" },
            ticks: {
              color: "#64748b",
              autoSkip: true,
              maxTicksLimit: isMobile() ? 6 : 8,
            },
          },
          y: {
            beginAtZero: false,
            min: yWin ? yWin.min : spec.yMin,
            max: yWin ? yWin.max : spec.yMax,
            grid: { color: "rgba(15,23,42,0.06)" },
            ticks: { color: "#64748b" },
            title: spec.yTitle
              ? { display: true, text: spec.yTitle, color: "#64748b" }
              : undefined,
          },
        },
      },
    };
  }

  function mountChart(spec, idx) {
    var chartId = "chemclaw-chart-" + idx;
    var canvas = document.getElementById(chartId);
    var panel = document.getElementById(chartId + "-panel");
    var wrap = document.getElementById(chartId + "-wrap");
    if (!canvas || !wrap) return;

    spec.$resolvedStages = resolvedStagesForSpec(spec);

    var config =
      spec.type === "candlestick" ? buildCandleConfig(spec) : buildSeriesConfig(spec);
    var chart = new Chart(canvas.getContext("2d"), config);
    var pinned = false;
    var hoverIndex = Math.max(0, (spec.labels || []).length - 1);
    var pointerDown = null;

    function applyIndex(index, pin) {
      hoverIndex = index;
      chart.$hoverIndex = index;
      if (typeof pin === "boolean") pinned = pin;
      updatePanel(panel, spec, index, pinned);
      updateCrosshairStatus(chartId, pinned);
      chart.update("none");
    }

    applyIndex(hoverIndex, false);

    var labels = spec.labels || [];
    var zoomWin = isMobile() ? MOBILE_WINDOW : MOBILE_WINDOW;
    if (labels.length > zoomWin && chart.options.plugins && chart.options.plugins.zoom) {
      var start = Math.max(0, labels.length - zoomWin);
      chart.zoomScale("x", { min: start, max: labels.length - 1 });
      if (spec.type === "candlestick") fitYToVisibleBars(chart, spec.ohlc || []);
      else
        fitYToVisibleSeries(
          chart,
          (spec.series || []).map(function (s) {
            return s.values || [];
          })
        );
      applyIndex(labels.length - 1, false);
    }

    wrap.addEventListener(
      "wheel",
      function (e) {
        if (e.target && e.target.closest && e.target.closest(".chart-axis-panel")) return;
        e.preventDefault();
      },
      { passive: false }
    );

    wrap.addEventListener("mousemove", function (e) {
      if (pinned) {
        chart.$hoverIndex = hoverIndex;
        return;
      }
      var index = indexFromClient(chart, canvas, spec, e.clientX, e.clientY);
      if (index == null) {
        applyIndex(Math.max(0, labels.length - 1), false);
        return;
      }
      applyIndex(index, false);
    });

    wrap.addEventListener("mouseleave", function () {
      if (!pinned) applyIndex(Math.max(0, labels.length - 1), false);
    });

    wrap.addEventListener("mousedown", function (e) {
      if (e.button !== 0) return;
      pointerDown = { x: e.clientX, y: e.clientY };
    });

    wrap.addEventListener("click", function (e) {
      if (pointerDown) {
        var dx = Math.abs(e.clientX - pointerDown.x);
        var dy = Math.abs(e.clientY - pointerDown.y);
        pointerDown = null;
        if (dx > 6 || dy > 6) return;
      }
      var index = indexFromClient(chart, canvas, spec, e.clientX, e.clientY);
      if (index == null) return;
      applyIndex(index, true);
    });

    wrap.addEventListener("dblclick", function (e) {
      e.preventDefault();
      pointerDown = null;
      var index = indexFromClient(chart, canvas, spec, e.clientX, e.clientY);
      if (index == null) applyIndex(Math.max(0, labels.length - 1), false);
      else applyIndex(index, false);
    });

    var btn = document.querySelector('[data-chart-fs="' + chartId + '"]');
    if (btn && wrap) {
      btn.addEventListener("click", function () {
        var req = wrap.requestFullscreen || wrap.webkitRequestFullscreen;
        if (document.fullscreenElement || document.webkitFullscreenElement) {
          (document.exitFullscreen || document.webkitExitFullscreen).call(document);
        } else if (req) {
          req.call(wrap);
        }
      });
    }
  }

  SPECS.forEach(mountChart);
})();
