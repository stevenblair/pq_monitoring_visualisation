/**
 * Author: Steven Blair, steven.m.blair@strath.ac.uk
 */


// TODO sometimes cumulative histogram shows nothing when Neutral visible - possible bug in Highcharts


// global functions
Number.prototype.nth = function() {
  if (this % 1) return this;
  var s = this % 100;
  if (s > 3 && s < 21) return this + 'th';
  switch(s % 10) {
    case 1: return this + 'st';
    case 2: return this + 'nd';
    case 3: return this + 'rd';
    default: return this + 'th';
  }
}

function linspace(d1, d2, n) {
  var j = 0;
  var L = [];
  
  while (j <= (n-1)) {
    var tmp1 = j * (d2 - d1) / (Math.floor(n) - 1);
    var tmp2 = Math.ceil((d1 + tmp1) * 10000) / 10000;
    L.push(tmp2);
    j = j + 1;
  }
  
  return L;
}

function sgn(x) {
  return (x > 0) - (x < 0);
}

// allow binding to "disabled" attribute on HTML select options
Ember.SelectOption.reopen({
  attributeBindings: ["value", "selected", "disabled"],
  disabled: function() {
    var content = this.get("content");
    return content.disabled || false;
  }.property("content.disabled")
});

window.App = Ember.Application.create();

App.Router.map(function() {
  this.resource("about");
});

// when entering a route, close the navbar menu
Ember.Route.reopen({
  activate: function() {
    if ($(".navbar-toggle").css("display") != "none") {
      $(".navbar-toggle").trigger("click");
    }
  }
});

App.IndexRoute = Ember.Route.extend({
  // define model as an array of monitors, from AJAX request
  model: function(params) {
    return Ember.$.getJSON("monitors").then(function(data) {
      var ret = [];
      data.forEach(function(d) {
        if (d.total_days > 0) {
          d.maxFrom = new Date(d.earliest_date * 1000);
          d.maxTo = new Date(d.latest_date * 1000);
          ret.push(d);
        }
      });
      return ret;
    });
  }
});

// support Bootstrap's active link style
App.NavView = Ember.View.extend({
  tagName: 'li',
  classNameBindings: ['active'],
  active: function() {
    return this.get('childViews.firstObject.active');
  }.property()
});

// initialise view
App.IndexView = Ember.View.extend({
  didInsertElement : function () {
    // after view has been added to DOM, select first monitoring location by default (if not specified)
    if (this.get("controller").get("location") == "") {
      var randomIndex = Math.floor(Math.random() * this.get("controller").get("content").length);//Math.random() * this.get("controller").get("content").length - 1);
      // console.log(randomIndex, this.get("controller").get("content").length);
      this.get("controller").set("location", this.get("controller").get("content").objectAt(randomIndex).monitor_name_index);
    }

    // initialise and validate parameters
    this.validateParams();
    
    // set up mouse wheel events
    this.get("controller").setMousewheelEvents();

    // signal that all initial parameter changes have been make
    this.get("controller").set("initialisedParams", true);

    // trigger first data request
    this.get("controller").update();
  },
  validateParams: function() {
    // TODO add more validation; set to default if wrong
    //      should call controller function to do this - to allow some validation at runtime too

    var plotTypeName = this.get("controller").get("plotTypeName");
    var from = this.get("controller").get("shownFromDate");
    var to = this.get("controller").get("shownToDate");

    // check if a date range has been manually set in URI
    if (this.get("controller").get("from") * 1000 != from.getTime()) {
      if (plotTypeName == "DAY_POLAR") {
        this.get("controller").set("firstPolarDaySelection", false);
      }
      else if (plotTypeName == "WAVEFORMS" || plotTypeName == "HARMONICS") {
        this.get("controller").set("firstWaveformSelection", false);
      }
    }

    // initialise "from" and "to" for URI query params
    from.setTime(this.get("controller").get("from") * 1000);
    this.get("controller").set("shownFromDate", from);
    to.setTime(this.get("controller").get("to") * 1000);
    this.get("controller").set("shownToDate", to);
  }
});

// allow properties to be added to each item in model array
App.MonitorItemController = Ember.ObjectController.extend({
  needs: 'Index',
  monitorFormattedName: function() {
    return this.get("primary_name") + ', ' + this.get("monitor_name_formatted") + ' (' + this.get("total_days") + ' days)';
  }.property("primary_name", "monitor_name_formatted", "total_days")
});

App.IndexController = Ember.ArrayController.extend({
  // link to controller for each item of underlying model
  itemController: "monitorItem",

  // constants
  SHOW_TOOLTIPS: false,
  SHOW_POINT_MARKER: false,

  // definitions of parameter and plot types
  parameterTypes: Ember.A([
    {
      "id": 0,
      "name": "Current",
      "units": "A",
      "label": ["Current_RMS_10_Cycle_Avg_A", "Current_RMS_10_Cycle_Min_A", "Current_RMS_10_Cycle_Max_A"],
      "labelThreePhase": ["L1_Current_RMS_1_2__1_cyc_Avg_A", "L2_Current_RMS_1_2__1_cyc_Avg_A", "L3_Current_RMS_1_2__1_cyc_Avg_A", "N_Current_RMS_1_2__1_cyc_Avg_A"],
      "supportsHarmomicPlots": true,
      "ranges": false,
      "minValue": 0.0,
      "plotBands": null,
      "forceYAxisZero": 0.0,
      "disabled": false
    }, {
      "id": 1,
      "name": "L-N voltage",
      "units": "V",
      "label": ["L_N_RMS_10_Cycle_Avg_V", "L_N_RMS_10_Cycle_Min_V", "L_N_RMS_10_Cycle_Max_V"],
      "labelThreePhase": ["L1_N_RMS_1_2__1_cyc_Avg_V", "L2_N_RMS_1_2__1_cyc_Avg_V", "L3_N_RMS_1_2__1_cyc_Avg_V", "N_E_RMS_1_2__1_cyc_Avg_V"],
      "supportsHarmomicPlots": true,
      "ranges": false,
      "minValue": null,
      "plotBands": [
        {
          from: 0.0,
          to: 207,
          color: 'red',
          label: {
              text: 'Lower statutory limit',
              style: {
                  color: '#606060'
              }
          }
        }, {
          from: 253,
          to: 500,
          color: 'red',
          label: {
              text: 'Upper statutory limit',
              style: {
                  color: '#606060'
              }
          }
        }],
      "disabled": false
    }, {
      "id": 2,
      "name": "Frequency, 1-cycle",
      "units": "Hz",
      "label": ["Frequency__1_cyc_Avg_Hz", "Frequency__1_cyc_Min_Hz", "Frequency__1_cyc_Max_Hz"],
      "labelThreePhase": null,
      "supportsHarmomicPlots": false,
      "ranges": true,
      "minValue": null,
      "plotBands": [
        {
          from: 0.0,
          to: 49.5,
          color: 'red',
          label: {
              text: 'Lower statutory limit',
              style: {
                  color: '#606060'
              }
          }
        }, {
          from: 49.5,
          to: 49.8,
          color: 'pink',
          label: {
              text: 'Lower operational limit',
              style: {
                  color: '#606060'
              }
          }
        }, {
          from: 50.2,
          to: 50.5,
          color: 'pink',
          label: {
              text: 'Upper operational limit',
              style: {
                  color: '#606060'
              }
          }
        }, {
          from: 50.5,
          to: 100.0,
          color: 'red',
          label: {
              text: 'Upper statutory limit',
              style: {
                  color: '#606060'
              }
          }
        }],
      "disabled": false
    }, {
      "id": 3,
      "name": "Apparent power",
      "units": "kVA",
      "label": ["Apparent_Power_10_Cycle_Avg_kVA", "Apparent_Power_10_Cycle_Min_kVA", "Apparent_Power_10_Cycle_Max_kVA"],
      "labelThreePhase": ["VA_L1_10_Cycle_Avg_kVA", "VA_L2_10_Cycle_Avg_kVA", "VA_L3_10_Cycle_Avg_kVA"],
      "supportsHarmomicPlots": false,
      "ranges": false,
      "minValue": null,
      "plotBands": null,
      "disabled": false
    }, {
      "id": 4,
      "name": "Real power",
      "units": "kW",
      "label": ["Real_Power_10_Cycle_Avg_kW", "Real_Power_10_Cycle_Min_kW", "Real_Power_10_Cycle_Max_kW"],
      "labelThreePhase": ["Real_Power_L1_10_Cycle_Avg_kW", "Real_Power_L2_10_Cycle_Avg_kW", "Real_Power_L3_10_Cycle_Avg_kW"],
      "supportsHarmomicPlots": false,
      "ranges": false,
      "minValue": null,
      "plotBands": null,
      "disabled": false
    }, {
      "id": 5,
      "name": "Reactive power",
      "units": "kvar",
      "label": ["Reactive_Power_10_Cycle_Avg_kVAR", "Reactive_Power_10_Cycle_Min_kVAR", "Reactive_Power_10_Cycle_Max_kVAR"],
      "labelThreePhase": ["VAR_L1_10_Cycle_Avg_kVAR", "VAR_L2_10_Cycle_Avg_kVAR", "VAR_L3_10_Cycle_Avg_kVAR"],
      "supportsHarmomicPlots": false,
      "ranges": false,
      "minValue": null,
      "plotBands": null,
      "disabled": false
    }, {
      "id": 6,
      "name": "Power factor",
      "units": "",
      "label": ["tPF_10_Cycle_Avg", "tPF_10_Cycle_Min", "tPF_10_Cycle_Max"],
      "labelThreePhase": ["tPF_L1_10_Cycle_Avg", "tPF_L2_10_Cycle_Avg", "tPF_L3_10_Cycle_Avg"],
      "supportsHarmomicPlots": false,
      "ranges": false,
      "minValue": null,
      "plotBands": null,
      "disabled": false
    }, {
      "id": 7,
      "name": "THD",
      "units": "%",
      "label": ["THD_V_Avg_perc", "THD_V_Min_perc", "THD_V_Max_perc"],
      "labelThreePhase": ["THD_V_L1_Avg_perc", "THD_V_L2_Avg_perc", "THD_V_L3_Avg_perc"],
      "supportsHarmomicPlots": false,
      "ranges": true,
      "minValue": 0.0,
      "plotBands": [
        {
          from: 5.0,
          to: 100.0,
          color: 'red',
          label: {
              text: 'Upper statutory limit',
              style: {
                  color: '#606060'
              }
          }
        }],
      "forceYAxisZero": 0.0,
      "disabled": false
    }, {
      "id": 8,
      "name": "TDD",
      "units": "%",
      "label": ["TDD_A_Avg_perc", "TDD_A_Min_perc", "TDD_A_Max_perc"],
      "labelThreePhase": ["TDD_A_L1_Avg_perc", "TDD_A_L2_Avg_perc", "TDD_A_L3_Avg_perc"],
      "supportsHarmomicPlots": false,
      "ranges": true,
      "minValue": 0.0,
      "plotBands": null,
      "forceYAxisZero": 0.0,
      "disabled": false
    }, {
      "id": 9,
      "name": "IEC negative-sequence voltage",
      "units": "%",
      "label": ["IEC_Negative_Sequence_V_Avg_perc", "IEC_Negative_Sequence_V_Min_perc", "IEC_Negative_Sequence_V_Max_perc"],
      "labelThreePhase": null,
      "supportsHarmomicPlots": false,
      "ranges": true,
      "minValue": 0.0,
      "plotBands": null,
      "forceYAxisZero": 0.0,
      "disabled": false
    }, {
      "id": 10,
      "name": "IEC zero-sequence voltage",
      "units": "%",
      "label": ["IEC_Zero_Sequence_V_Avg_perc", "IEC_Zero_Sequence_V_Min_perc", "IEC_Zero_Sequence_V_Max_perc"],
      "labelThreePhase": null,
      "supportsHarmomicPlots": false,
      "ranges": true,
      "minValue": 0.0,
      "plotBands": null,
      "forceYAxisZero": 0.0,
      "disabled": false
    }, {
      "id": 11,
      "name": "IEC negative-sequence current",
      "units": "%",
      "label": ["IEC_Negative_Sequence_A_Avg_perc", "IEC_Negative_Sequence_A_Min_perc", "IEC_Negative_Sequence_A_Max_perc"],
      "labelThreePhase": null,
      "supportsHarmomicPlots": false,
      "ranges": true,
      "minValue": 0.0,
      "plotBands": null,
      "forceYAxisZero": 0.0,
      "disabled": false
    }, {
      "id": 12,
      "name": "IEC zero-sequence current",
      "units": "%",
      "label": ["IEC_Zero_Sequence_A_Avg_perc", "IEC_Zero_Sequence_A_Min_perc", "IEC_Zero_Sequence_A_Max_perc"],
      "labelThreePhase": null,
      "supportsHarmomicPlots": false,
      "ranges": true,
      "minValue": 0.0,
      "plotBands": null,
      "forceYAxisZero": 0.0,
      "disabled": false
    }, {
      "id": 13,
      "name": "Flicker instantaneous (Pinst)",
      "units": "",
      "label": ["Flicker_P_inst_Avg", "Flicker_P_inst_Min", "Flicker_P_inst_Max"],
      "labelThreePhase": ["P_inst_L1_Avg", "P_inst_L2_Avg", "P_inst_L3_Avg"],
      "supportsHarmomicPlots": false,
      "ranges": false,
      "minValue": 0.0,
      "plotBands": null,
      "forceYAxisZero": 0.0,
      "disabled": false
    }, {
      "id": 14,
      "name": "Flicker short-term (Pst)",
      "units": "",
      "label": ["Flicker_P_st_Avg", "Flicker_P_st_Min", "Flicker_P_st_Max"],
      "labelThreePhase": ["P_st_L1_Avg", "P_st_L2_Avg", "P_st_L3_Avg"],
      "supportsHarmomicPlots": false,
      "ranges": false,
      "minValue": 0.0,
      "plotBands": null,
      "forceYAxisZero": 0.0,
      "disabled": false
    }, {
      "id": 15,
      "name": "Flicker long-term (Plt)",
      "units": "",
      "label": ["Flicker_P_lt_Avg", "Flicker_P_lt_Min", "Flicker_P_lt_Max"],
      "labelThreePhase": ["P_lt_L1_Avg", "P_lt_L2_Avg", "P_lt_L3_Avg"],
      "supportsHarmomicPlots": false,
      "ranges": false,
      "minValue": 0.0,
      "plotBands": null,
      "forceYAxisZero": 0.0,
      "disabled": false
    }
  ]),
  plotTypes: Ember.A([
    {
      "id": 0,
      "name": "Time series (average of individual phases, with min-max range)",
      "value": "TIME_SERIES_AVERAGE",
      "requiresThreePhasePlots": false,
      "supportsHarmomicPlots": false,
      "supportsPerUnit": false,
      "supportsPlotZoom": true,
      "supportsHistogram": true,
      "supportsEvents": true,
      "disabled": false,
      "command": "rms"
    }, {
      "id": 1,
      "name": "Time series (three-phase)",
      "value": "TIME_SERIES",
      "requiresThreePhasePlots": true,
      "supportsHarmomicPlots": false,
      "supportsPerUnit": false,
      "supportsPlotZoom": true,
      "supportsHistogram": true,
      "supportsEvents": true,
      "disabled": false,
      "command": "rms"
    }, {
      "id": 2,
      "name": "Day polar plot (three-phase)",
      "value": "DAY_POLAR",
      "requiresThreePhasePlots": true,
      "supportsHarmomicPlots": false,
      "supportsPerUnit": false,
      "supportsPlotZoom": false,
      "supportsHistogram": true,
      "supportsEvents": false,
      "disabled": false,
      "command": "rms"
    }, {
      "id": 3,
      "name": "Heat map (average)",
      "value": "HEAT_MAP",
      "requiresThreePhasePlots": false,
      "supportsHarmomicPlots": false,
      "supportsPerUnit": false,
      "supportsPlotZoom": false,
      "supportsHistogram": false,
      "supportsEvents": false,
      "disabled": false,
      "command": "heatmap"
    }, {
      "id": 4,
      "name": "Instantaneous harmonic spectra",
      "value": "HARMONICS",
      "requiresThreePhasePlots": false,
      "supportsHarmomicPlots": true,
      "supportsPerUnit": true,
      "supportsPlotZoom": false,
      "supportsHistogram": false,
      "supportsEvents": false,
      "disabled": false,
      "command": "harmonics"
    }, {
      "id": 5,
      "name": "Detailed waveforms (estimated from harmonic profile)",
      "value": "WAVEFORMS",
      "requiresThreePhasePlots": false,
      "supportsHarmomicPlots": true,
      "supportsPerUnit": false,
      "supportsPlotZoom": false,
      "supportsHistogram": false,
      "supportsEvents": false,
      "disabled": false,
      "command": "waveforms"
    }, {
      "id": 6,
      "name": "Harmonics time-series",
      "value": "HARMONICS_TRENDS",
      "requiresThreePhasePlots": false,
      "supportsHarmomicPlots": true,
      "supportsPerUnit": true,
      "supportsPlotZoom": true,
      "supportsHistogram": false,
      "supportsEvents": true,
      "disabled": false,
      "command": "harmonicstrends"
    }
  ]),
  eventTypes: Ember.A([
    {
      "label": "NOP_opened",
      "name": "NOP opened",
      "plotColor": "green",
      "markerSymbol": "circle",
      "condition": "",
      "y": 80
    }, 
    {
      "label": "NOP_closed",
      "name": "NOP closed",
      "plotColor": "green",
      "markerSymbol": "square",
      "condition": "",
      "y": 70
    }, 
    {
      "label": "Voltage Swell",
      "name": "Over-voltage",
      "plotColor": "rgba(254, 178, 76, 0.8)",
      "markerSymbol": "triangle",
      "condition": "> 1.1 pu of nominal",
      "y": 60
    }, {
      "label": "Voltage Sag",
      "name": "Under-voltage",
      "plotColor": "rgba(254, 178, 76, 0.8)",
      "markerSymbol": "triangle-down",
      "condition": "< 0.9 pu of nominal",
      "y": 50
    }, {
      "label": "Over-frequency",
      "name": "Over-frequency",
      "plotColor": "rgba(36, 78, 198, 0.8)",
      "markerSymbol": "triangle",
      "condition": "> 50.25 Hz of nominal",
      "y": 40
    }, {
      "label": "Under-frequency",
      "name": "Under-frequency",
      "plotColor": "rgba(36, 78, 198, 0.8)",
      "markerSymbol": "triangle-down",
      "condition": "< 49.75 Hz of nominal",
      "y": 30
    }, {
      "label": "Phase Current Trigger",
      "name": "Phase over-current",
      "plotColor": "rgba(180, 33, 38, 0.8)",
      "markerSymbol": "triangle",
      "condition": "> 500 A",
      "y": 20
    }, {
      "label": "Neutral Current Trigger",
      "name": "Neutral over-current",
      "plotColor": "rgba(180, 33, 38, 0.8)",
      "markerSymbol": "triangle",
      "condition": "> 500 A",
      "y": 10
    }, {
      "label": "Waveshape Change",
      "name": "Waveshape change",
      "plotColor": "rgba(117, 107, 177, 0.8)",
      "markerSymbol": "diamond",
      "condition": "0.2 pu change in RMS voltage",
      "y": 0
    }
  ]),

  // definition of query parameters in URI
  queryParams: [
    "location",
    "parameterType",
    "plotType",
    "showHistogram",
    "histogramIsCumulative",
    "showEvents",
    "showNeutral",
    "showFundamental",
    "perUnit",
    "showInterharmonics",
    "from",
    "to",
    "eventWaveformTime"
  ],
  location: "",
  parameterType: 0,
  plotType: 0,
  showHistogram: false,
  histogramIsCumulative: false,
  showEvents: false,
  showNeutral: false,
  showFundamental: true,
  perUnit: false,
  showInterharmonics: false,
  from: Math.round(new Date(2013, 0, 1).getTime() / 1000),
  to: Math.round(new Date(2015, 0, 1).getTime() / 1000),
  eventWaveformTime: null,

  // additional controller state variables
  initialisedParams: false,
  hasNeutral: false,
  isReset: false,
  requestURI: null,
  firstPolarDaySelection: true,
  firstWaveformSelection: true,
  isNewPlotType: true,
  oldPlotTypeName: "",
  forcedDateRange: true,
  forceYAxisZero: false,
  skipCallback: false,
  extremeFromDate: new Date(2013, 0, 1),
  extremeToDate: new Date(2015, 0, 1),
  shownFromDate: new Date(2013, 0, 1),
  shownToDate: new Date(2015, 0, 1),
  scheduleUpdateEvents: true,
  showEventPower: false,

  // helper observers and properties
  fromSet: function() {
    this.set("from", Math.round(this.get("shownFromDate").getTime() / 1000));
  }.observes("shownFromDate"),
  toSet: function() {
    this.set("to", Math.round(this.get("shownToDate").getTime() / 1000));
  }.observes("shownToDate"),
  plotTypeName: function() {
    return this.get("plotTypes").objectAt(this.get("plotType")).value;
  }.property("plotType"),
  monitor: function() {
    var monitors = this.get("content");
    for (var i = 0; i < monitors.length; i++) {
      if (monitors[i].monitor_name_index === this.get("location")) {
        return monitors[i];
      }
    }
    return null;
  }.property("location"),

  // build URI for requesting data, based on present settings
  requestURI: function() {
    var monitor = this.get("monitor");
    var parameterType = this.get("parameterType");
    var parameter = this.get("parameterTypes").objectAt(this.get("parameterType"));
    var plotTypeName = this.get("plotTypeName");
    var shownFromDate = this.get("shownFromDate");
    var shownToDate = this.get("shownToDate");
    var command = this.get("plotTypes").objectAt(this.get("plotType")).command;

    if (monitor == null) {
      console.log("monitor == null");
    }

    var requestURI = command + "/" + monitor.monitor_name_index;
    
    var label = parameter["label"].join('/');
    if (plotTypeName == "TIME_SERIES") {
      if (parameter["labelThreePhase"] != null) {
        label = parameter["labelThreePhase"].join('/');
      }
    }
    else if (plotTypeName == "DAY_POLAR") {
      if (parameter["labelThreePhase"] != null) {
        label = parameter["labelThreePhase"].join('/');
      }
    }
    else if (plotTypeName == "HEAT_MAP") {
      label = parameter["label"][0];
    }

    if (plotTypeName == "TIME_SERIES" || plotTypeName == "TIME_SERIES_AVERAGE") {
      requestURI += "/from/" + this.convertDateToString(shownFromDate) + "/to/" + this.convertDateToString(shownToDate) + "/" + label;
    }
    else if (plotTypeName == "DAY_POLAR") {
      var earliestDate;
      var earliestDatePlusOneDay;

      if (this.get("firstPolarDaySelection")) {
        this.set("firstPolarDaySelection", false);

        if (this.get("showEvents") && this.get("eventWaveformTime") != null) {
          earliestDate = new Date(this.get("eventWaveformTime") * 1000);
          // round to start of day
          earliestDate = new Date(earliestDate.getFullYear(), earliestDate.getMonth(), earliestDate.getDate());
        }
        else {
          earliestDate = new Date(monitor.earliest_date * 1000);
          // add one day to improve chance of getting a full day of valid data
          earliestDate = new Date(earliestDate.getFullYear(), earliestDate.getMonth(), earliestDate.getDate() + 1);
        }
        earliestDatePlusOneDay = new Date(earliestDate.getTime() + (24 * 60 * 60 * 1000) - (5 * 60 * 1000));

        this.set("shownFromDate", earliestDate);
        this.set("shownToDate", earliestDatePlusOneDay);
      }
      else {
        earliestDate = new Date(shownFromDate.getTime());
        earliestDatePlusOneDay = new Date(earliestDate.getTime() + (24 * 60 * 60 * 1000) - (5 * 60 * 1000));
      }
      requestURI += "/from/" + this.convertDateToString(earliestDate) + "/to/" + this.convertDateToString(new Date(earliestDatePlusOneDay)) + "/" + label;
    }
    else if (plotTypeName == "HEAT_MAP") {
      requestURI += "/" + label;
    }
    else if (plotTypeName == "WAVEFORMS" || plotTypeName == "HARMONICS") {
      var waveformType = 'voltage';
      if (parameterType == 0) {
        waveformType = 'current';
      }

      if (this.get("firstWaveformSelection")) {
        this.set("firstWaveformSelection", false);

        var waveformDate = new Date(monitor.harmonics_earliest_date * 1000);

        if (this.get("showEvents") && this.get("eventWaveformTime") != null) {
          waveformDate = new Date(this.get("eventWaveformTime") * 1000);
          // // round to start of day
          // waveformDate = new Date(waveformDate.getFullYear(), waveformDate.getMonth(), waveformDate.getDate());

        // round up to a valid 15-minute interval
          waveformDate.setMinutes(((parseInt((waveformDate.getMinutes() + 7.5)/15) * 15) % 60) + 15);
          waveformDate.setMinutes(0);
          waveformDate.setSeconds(0);
          waveformDate.setMilliseconds(0);
          // waveformDate.setHours(waveformDate.getHours() + 1);
        }
        shownFromDate = waveformDate;
        this.set("shownFromDate", waveformDate);
      }

      var firstFifteenMinute = this.convertDateToString(shownFromDate);
      requestURI += "/" + waveformType + "/" + firstFifteenMinute;

      if (plotTypeName == "HARMONICS") {
        if (!this.get("showFundamental")) {
          requestURI += "/nofundamental";
        }
        if (this.get("perUnit")) {
          requestURI += "/perunit";
        }
        if (this.get("showInterharmonics")) {
          requestURI += "/interharmonics";
        }
      }
    }
    else if (plotTypeName == "HARMONICS_TRENDS") {
      var chart = $("#container").highcharts();
      if (chart) {
        chart.showLoading("Loading...");
      }

      var waveformType = 'voltage';
      if (parameterType == 0) {
        waveformType = 'current';
      }
      requestURI += "/" + waveformType + "/from/" + this.convertDateToString(shownFromDate) + "/to/" + this.convertDateToString(shownToDate);

      if (this.get("perUnit")) {
        requestURI += "/perunit";
      }
    }

    return requestURI;
  }.property("location", "parameterType", "plotType", "shownFromDate", "shownToDate", "showFundamental", "perUnit", "showInterharmonics"),
  convertDateToString: function(date) {
    return date.getUTCFullYear() + '/' + ('0' + (date.getMonth()+1)).slice(-2) + '/' + ('0' + date.getDate()).slice(-2) + '/' + ('0' + (date.getHours())).slice(-2) + ':' + ('0' + (date.getMinutes())).slice(-2) + ':' + ('0' + (date.getSeconds())).slice(-2);
  },
  
  // main settings: monitoring device location, parameter type, and plot type
  locationChange: function() {
    this.setZoom();

    if (this.get("plotTypeName") == "DAY_POLAR") {
      this.set("firstPolarDaySelection", true);
    }
    if (this.get("plotTypeName") == "WAVEFORMS" || this.get("plotTypeName") == "HARMONICS") {
      this.set("firstWaveformSelection", true);
    }

    if (this.get("initialisedParams")) {
      this.set("eventWaveformTime", null);
      this.update();
    }

    this.set("scheduleUpdateEvents", true);
  }.observes("location"),
  parameterTypeChange: function() {
    this.setZoom();

    var isThreePhase = this.get("parameterTypes").objectAt(this.get("parameterType")).labelThreePhase != null;
    var isHarmonicPlot = this.get("parameterTypes").objectAt(this.get("parameterType")).supportsHarmomicPlots;

    this.get("plotTypes").forEach(function(p) {
      var shown = true;
      if ((!isHarmonicPlot && isHarmonicPlot != p.supportsHarmomicPlots) || (!isThreePhase && isThreePhase != p.requiresThreePhasePlots)) {
        Ember.set(p, 'disabled', true);
      }
      else {
        Ember.set(p, 'disabled', false);
      }
    });

    var labelThreePhase = this.get("parameterTypes").objectAt(this.get("parameterType")).labelThreePhase;
    if (labelThreePhase && labelThreePhase.length == 4) {
      this.set("hasNeutral", true);
    }
    else {
      this.set("hasNeutral", false);
      this.set("showNeutral", false);  // by default, suppress neutral series to avoid possible confusion
    }

    if (this.get("initialisedParams")) {
      this.update();
    }
  }.observes("parameterType"),
  plotTypeChange: function() {
    var oldPlotTypeName = this.get("oldPlotTypeName");
    this.set("isNewPlotType", true);

    this.setZoom();

    if (this.get("plotTypeName") != "DAY_POLAR") {
      this.set("firstPolarDaySelection", true);
    }

    if (oldPlotTypeName != "HARMONICS" && oldPlotTypeName != "WAVEFORMS") {
      this.set("firstWaveformSelection", true);
    }

    if (this.get("plotTypeName") == "TIME_SERIES" || this.get("plotTypeName") == "DAY_POLAR") {
      this.get("parameterTypes").forEach(function(p) {
        if (p.labelThreePhase == null) {
          Ember.set(p, 'disabled', true);
        }
        else {
          Ember.set(p, 'disabled', false);
        }
      });
    }
    else if (this.get("plotTypeName") == "WAVEFORMS" || this.get("plotTypeName") == "HARMONICS" || this.get("plotTypeName") == "HARMONICS_TRENDS") {
      this.get("parameterTypes").forEach(function(p) {
        if (p.supportsHarmomicPlots) {
          Ember.set(p, 'disabled', false);
        }
        else {
          Ember.set(p, 'disabled', true);
        }
      });
    }
    else {
      this.get("parameterTypes").forEach(function(p) {
        Ember.set(p, 'disabled', false);
      });
    }

    if (this.get("initialisedParams")) {
      this.update();
    }

    this.set("oldPlotTypeName", this.get("plotTypeName"));

    this.set("scheduleUpdateEvents", true);
  }.observes("plotType"),
  setZoom: function() {
    var chart = $('#container').highcharts();
    if (chart && chart.resetZoomButton == null && this.get("plotTypes").objectAt(this.get("plotType")).supportsPlotZoom) {
      this.set("shownFromDate", this.get("extremeFromDate"));
      this.set("shownToDate", this.get("extremeToDate"));
    }
  },

  // histogram settings
  cumulativeChange: function() {
    if (this.get("histogramIsCumulative") && !this.get("showHistogram")) {
      this.set("showHistogram", true);
    }
  }.observes("histogramIsCumulative"),
  showHistogramContainer: function() {
    return this.get("showHistogramButtons") && this.get("showHistogram");
  }.property("showHistogram", "showHistogramButtons"),
  showHistogramButtons: function() {
    return this.get("plotTypes").objectAt(this.get("plotType")).supportsHistogram;
  }.property("plotType"),

  showEventButtons: function() {
    return this.get("plotTypes").objectAt(this.get("plotType")).supportsEvents;
  }.property("plotType"),

  // harmonics settings
  showFundamentalChange: function() {
    if (this.get("plotTypeName") == "HARMONICS_TRENDS") {
      var chart = $('#container').highcharts();
      if (chart) {
        if (this.get("showFundamental")) {
          chart.series[0].show();
        }
        else {
          chart.series[0].hide();
        }
      }
    }
    else {
      if (this.get("initialisedParams")) {
        this.update();
      }
    }
  }.observes("showFundamental"),
  harmonicsSettingsChange: function() {
    if (this.get("initialisedParams")) {
      this.update();
    }
  }.observes("perUnit", "showInterharmonics"),
  showHarmonicsButtons: function() {
    if (this.get("plotTypeName") == "HARMONICS" || this.get("plotTypeName") == "HARMONICS_TRENDS") {
      return true;
    }
    return false;
  }.property('plotType'),
  showInterharmonicsButton: function() {
    if (this.get("plotTypeName") == "HARMONICS") {
      return true;
    }
    return false;
  }.property('plotType'),
  interharmonicsButtonSelected: function() {
    return this.get("showInterharmonics") && this.get("plotTypeName") == "HARMONICS";
  }.property("showInterharmonics", "showHarmonicsButtons"),

  // configure mouse wheel events
  setMousewheelEvents: function() {
    $('#content').mousewheel(function(event) {
      var plotTypeName = this.get("plotTypeName");
      var shownFromDate = this.get("shownFromDate");
      var shownToDate = this.get("shownToDate");

      if (plotTypeName == "DAY_POLAR") {
        var direction = 1 * sgn(event.deltaY);
        var newFromDate = shownFromDate.getDate() + direction;
        var newToDate = shownToDate.getDate() + direction;

        var newShownFromDate = new Date(shownFromDate.getTime()).setDate(newFromDate);
        var newShownToDate = new Date(shownToDate.getTime()).setDate(newToDate);

        // ensure dates within valid data range
        if ((direction > 0 && newShownToDate < this.get("monitor").maxTo) || (direction < 0 && newShownFromDate > this.get("monitor").maxFrom)) {
          this.set("shownFromDate", new Date(newShownFromDate));
          this.set("shownToDate", new Date(newShownToDate));
          this.update();
        }
      }
      else if (plotTypeName == "WAVEFORMS" || plotTypeName == "HARMONICS") {
        var direction = 1 * sgn(event.deltaY);
        var newShownFromDate = new Date(shownFromDate.getTime());           // copy existing date
        newShownFromDate.setHours(newShownFromDate.getHours() + direction);

        // ensure date within valid data range
        if ((direction > 0 && newShownFromDate < this.get("monitor").maxTo) || (direction < 0 && newShownFromDate > this.get("monitor").maxFrom)) {
          this.set("shownFromDate", new Date(newShownFromDate));
          this.update();
        }
      }
    }.bind(this));
  },

  // update plot data from server
  update: function () {
    var requestURI = this.get("requestURI");
    var parameter = this.get("parameterTypes").objectAt(this.get("parameterType"));
    var plotType = this.get("plotTypes").objectAt(this.get("plotType"));
    var plotTypeName = this.get("plotTypeName");
    var yAxisLabel = parameter["name"] + " (" + parameter["units"] + ")";
    var isThreePhase = (parameter["labelThreePhase"] != null);

    if (parameter["units"] == "") {
      yAxisLabel = parameter["name"];
    }
    else if (parameter.supportsHarmomicPlots && plotType.supportsPerUnit && this.get("perUnit")) {
      yAxisLabel = parameter["name"] + " (%)";
    }

    Ember.$.getJSON(requestURI, function(data) {
      if (plotTypeName == "TIME_SERIES_AVERAGE") {
        this.createPlotAverage(yAxisLabel, data.data);
      }
      else if (plotTypeName == "TIME_SERIES" && isThreePhase) {
        this.createPlotThreePhase(yAxisLabel, data.data);
      }
      else if (plotTypeName == "DAY_POLAR") {
        this.createPlotDayPolar(yAxisLabel, data.data, isThreePhase);
      }
      else if (plotTypeName == "HEAT_MAP") {
        this.createPlotHeatMap(yAxisLabel, data.data, parameter["name"], parameter["units"]);
      }
      else if (plotTypeName == "WAVEFORMS") {
        this.createPlotWaveform(yAxisLabel, data.data);
      }
      else if (plotTypeName == "HARMONICS") {
        this.createPlotHarmonics(yAxisLabel, data.data);
      }
      else if (plotTypeName == "HARMONICS_TRENDS") {
        this.createPlotHarmonicsTrends(yAxisLabel, data.data, data.harmonic_numbers);
      }

      this.updateHistogram();

      var chart = $("#container").highcharts();
      var supported = this.get("plotTypes").objectAt(this.get("plotType")).supportsEvents;
      if (this.get("scheduleUpdateEvents") || (this.get("showEvents") && supported && chart == null) || (this.get("showEvents") && supported && chart && chart.series.length <= 4)) {
        this.set("scheduleUpdateEvents", false);
        this.updateEvents();
      }
    }.bind(this));
  },

  // histogram plot functions
  getPhaseHistogramData: function(plotData) {
    if (plotData.length == 0) {
      return [];
    }

    var histDataRaw = [];
    plotData.forEach(function(v) {
      if (v.y != null) {
        histDataRaw.push(v.y);
      }
    });

    var bins = [];
    var minValue = this.get("parameterTypes").objectAt(this.get("parameterType")).minValue;
    if (minValue != null) {
      bins = linspace(minValue, Math.max.apply(Math, histDataRaw), 40);
    }
    else {
      // console.log("min:", Math.min.apply(Math, histDataRaw), "max:", Math.max.apply(Math, histDataRaw));
      bins = linspace(Math.min.apply(Math, histDataRaw), Math.max.apply(Math, histDataRaw), 40);
    }

    // console.log("histDataRaw", histDataRaw);
    var histData = histogram({
      data: histDataRaw,
      bins: bins
    });

    // console.log("histData", histData);
    // console.log("bins", bins);

    var totalHistogramItems = histDataRaw.length;
    var histDataForPlot = [];
    var histogramIsCumulative = this.get("histogramIsCumulative");
    histData.forEach(function(v) {
      if (histogramIsCumulative) {
        var previousValue = 0.0;
        if (histDataForPlot.length > 0) {
          previousValue = histDataForPlot[histDataForPlot.length - 1][1];
        }
        histDataForPlot.push([v.x, previousValue + 100.0 * v.y / totalHistogramItems]);
      }
      else {
        histDataForPlot.push([v.x, 100.0 * v.y / totalHistogramItems]);
      }
    });

    return histDataForPlot;
  },
  updateHistogram: function() {
    var plotTypeName = this.get("plotTypeName");
    var parameterType = this.get("parameterType");

    var maxValue = null;
    if (this.get("histogramIsCumulative")) {
      maxValue = 100.0;
    }
    var minXValue = this.get("parameterTypes").objectAt(this.get("parameterType")).minValue;

    if (this.get("showHistogram")) {
      var chart = $("#container").highcharts();
      if (this.get("hasNeutral")) {
        // console.log("N hist:", this.getPhaseHistogramData(chart.series[3].data));
      }

      if (chart) {
        var options = {};
        if (plotTypeName == "TIME_SERIES" || plotTypeName == "DAY_POLAR") {
          options = {
            chart: {
              type: 'area',
              inverted: true
            },
            title: {
              text: ''
            },
            yAxis: {
              max: maxValue,
              title: {
                text: '%'
              }
            },
            tooltip: {
              enabled: false
            },
            legend: {
              enabled: false
            },
            xAxis: {
              min: minXValue,
              title: {
                text: chart.options.yAxis[0].title.text
              }
            },
            series: [{
              name: 'Phase A',
              data: this.getPhaseHistogramData(chart.series[0].data),
              color: 'rgba(180, 33, 38, 0.8)',
              marker: {
                enabled: false,
                radius: 1,
                states: {
                  hover: {
                    enabled: false
                  }
                }
              },
              zIndex: 1
            }, {
              name: 'Phase B',
              data: this.getPhaseHistogramData(chart.series[1].data),
              color: 'rgba(222, 215, 20, 0.8)',
              marker: {
                enabled: false,
                radius: 1,
                states: {
                  hover: {
                    enabled: false
                  }
                }
              },
              zIndex: 1
            }, {
              name: 'Phase C',
              data: this.getPhaseHistogramData(chart.series[2].data),
              color: 'rgba(36, 78, 198, 0.8)',
              marker: {
                enabled: false,
                radius: 1,
                states: {
                  hover: {
                    enabled: false
                  }
                }
              },
              zIndex: 1
            }, {
              name: 'Neutral',
              visible: this.get("showNeutral"),
              data: this.getPhaseHistogramData(chart.series[3].data),
              color: 'rgba(40, 40, 40, 0.8)',
              marker: {
                enabled: false,
                radius: 1,
                states: {
                  hover: {
                    enabled: false
                  }
                }
              },
              zIndex: 1
            }],
            plotOptions: {
              series: {
                enableMouseTracking: this.get("SHOW_POINT_MARKER"),
                states: {
                  hover: {
                    enabled: false
                  }
                }
              }
            },
            credits: false
          };
        }
        else {
          options = {
            chart: {
              type: 'area',
              inverted: true
            },
            title: {
              text: ''
            },
            yAxis: {
              max: maxValue,
              title: {
                text: '%'
              },
              plotBands: null
            },
            tooltip: {
              enabled: false
            },
            legend: {
              enabled: false
            },
            xAxis: {
              min: minXValue,
              title: {
                text: chart.options.yAxis[0].title.text
              }
            },
            series: [{
              name: '',
              data: this.getPhaseHistogramData(chart.series[0].data),
              marker: {
                enabled: false,
                radius: 1,
                states: {
                  hover: {
                    enabled: false
                  }
                }
              },
              zIndex: 1
            }],
            plotOptions: {
              series: {
                enableMouseTracking: this.get("SHOW_POINT_MARKER"),
                states: {
                  hover: {
                    enabled: false
                  }
                }
              }
            },
            credits: false
          };
        }
        // console.log("N length:", chart.series[3].data.length);

        var histogramChart = $('#container-histogram').highcharts();
        if (histogramChart && !this.get("isNewPlotType")) {
          histogramChart.xAxis[0].setTitle({text: chart.options.yAxis[0].title.text}, false);
          histogramChart.xAxis[0].update({min: minXValue}, false);
          histogramChart.yAxis[0].update({max: maxValue}, false);

          if (plotTypeName == "TIME_SERIES" || plotTypeName == "DAY_POLAR") {
            histogramChart.series[0].setData(this.getPhaseHistogramData(chart.series[0].data), false);
            histogramChart.series[1].setData(this.getPhaseHistogramData(chart.series[1].data), false);
            histogramChart.series[2].setData(this.getPhaseHistogramData(chart.series[2].data), false);
            histogramChart.series[3].setData(this.getPhaseHistogramData(chart.series[3].data), false);
          }
          else {
            histogramChart.series[0].setData(this.getPhaseHistogramData(chart.series[0].data), false);
          }
          histogramChart.redraw();
        }
        else {
          $('#container-histogram').highcharts(options);
          this.set("isNewPlotType", false);
        }
      }
      else {
        var histogramChart = $('#container-histogram').highcharts();
        if (histogramChart) {
          histogramChart.destroy();
        }
      }
    }

    // force window resize event, which is delayed slightly
    Ember.run.later((function() {
      $(window).trigger("resize");
    }), 50);
  }.observes("showHistogram", "histogramIsCumulative", "showNeutral"),
  updateHistogramNeutral: function() {
    // console.log("updateHistogramNeutral()");
    var histogramChart = $("#container-histogram").highcharts();
    if (histogramChart && histogramChart.series[3]) {
      if (this.get("hasNeutral") && this.get("showNeutral")) {
        histogramChart.series[3].setVisible(true, true);
      }
      else {
        histogramChart.series[3].setVisible(false, true);
      }
    }
  }.observes("hasNeutral", "showNeutral"),

  eventDurationFormatter: function(duration_ms) {
    var valueStr = "0";
    if (duration_ms < 1000) {
      valueStr = Math.round(duration_ms) + " ms";
    }
    else {
      valueStr = (duration_ms / 1000.0).toFixed(1) + " s";
    }
    return valueStr; 
  },
  arrMul: function(a, b) {
    // TODO bound checking
    // TODO average over 128 samples (or 64?)
    // TODO neutral voltage should be calculated explicitly?

    var ret = [];
    for (var i = 0; i < a.length; i++) {
      ret.push((a[i] * b[i]) / 1000.0);
    }
    return ret;
  },
  zeros: function(len) {
    var data = [];
    for(var i = 0; i < len; i++) {
      data.push(0.0);
    }
    return data;
  },
  createEventWaveforms: function() {
    var timestamp = this.get("eventWaveformTime");
    if (this.get("showEvents") && this.get("monitor") && timestamp) {
      Ember.$.getJSON("event/" + this.get("monitor").monitor_name_index + "/" + timestamp).then(function(data) {
        var con = window.App.__container__.lookup('controller:index');

        if (con.showEventPower) {
          var P_inst_A = con.arrMul(data['L1_N__V'], data['L1_Amp__A']);
          var P_inst_B = con.arrMul(data['L2_N__V'], data['L2_Amp__A']);
          var P_inst_C = con.arrMul(data['L3_N__V'], data['L3_Amp__A']);
        }

        con.createEventWaveformPlot("V", data['Milliseconds'], data['L1_N__V'], data['L2_N__V'], data['L3_N__V'], data['N_E__V'], data["two_part"]);
        con.createEventWaveformPlot("I", data['Milliseconds'], data['L1_Amp__A'], data['L2_Amp__A'], data['L3_Amp__A'], data['N_Amp__A'], data["two_part"]);
        

        if (con.showEventPower) {
          con.createEventWaveformPlot("P", data['Milliseconds'], P_inst_A, P_inst_B, P_inst_C, null, data["two_part"]);

          // TODO compute per half-cycle?
          var Pa = con.zeros(16), Pb = con.zeros(16), Pc = con.zeros(16);
          var Qa = con.zeros(16), Qb = con.zeros(16), Qc = con.zeros(16);
          var Sa = con.zeros(16), Sb = con.zeros(16), Sc = con.zeros(16);

          // loop through each cycle
          for (var c = 0; c < 16; c++) {
            var Va = 0.0, Vb = 0.0, Vc = 0.0;
            var Ia = 0.0, Ib = 0.0, Ic = 0.0;

            // loop through each sample in cycle
            for (var i = 0; i < 128; i++) {
              Va += data['L1_N__V'][i + 128 * c] * data['L1_N__V'][i + 128 * c];
              Vb += data['L2_N__V'][i + 128 * c] * data['L2_N__V'][i + 128 * c];
              Vc += data['L3_N__V'][i + 128 * c] * data['L3_N__V'][i + 128 * c];
              Ia += data['L1_Amp__A'][i + 128 * c] * data['L1_Amp__A'][i + 128 * c];
              Ib += data['L2_Amp__A'][i + 128 * c] * data['L2_Amp__A'][i + 128 * c];
              Ic += data['L3_Amp__A'][i + 128 * c] * data['L3_Amp__A'][i + 128 * c];

              Pa[c] += P_inst_A[i + 128 * c];
              Pb[c] += P_inst_B[i + 128 * c];
              Pc[c] += P_inst_C[i + 128 * c];
            }

            Va = Math.sqrt(Va / 128);
            Vb = Math.sqrt(Vb / 128);
            Vc = Math.sqrt(Vc / 128);
            Ia = Math.sqrt(Ia / 128);
            Ib = Math.sqrt(Ib / 128);
            Ic = Math.sqrt(Ic / 128);
            Sa[c] = Va * Ia / 1000.0;
            Sb[c] = Vb * Ib / 1000.0;
            Sc[c] = Vc * Ic / 1000.0;
            // console.log(c, "V RMS:", Va, Vb, Vc);
            // console.log(c, "I RMS:", Ia, Ib, Ic);
            console.log(c, "S (kVA):", Sa[c], Sb[c], Sc[c]);

            Pa[c] = Pa[c] / 128;
            Pb[c] = Pb[c] / 128;
            Pc[c] = Pc[c] / 128;
            console.log(c, "P (kW):", Pa[c], Pb[c], Pc[c]);

            Qa[c] = Math.sqrt(Sa[c] * Sa[c] - Pa[c] * Pa[c]);
            Qb[c] = Math.sqrt(Sb[c] * Sb[c] - Pb[c] * Pb[c]);
            Qc[c] = Math.sqrt(Sc[c] * Sc[c] - Pc[c] * Pc[c]);
            console.log(c, "Q (kvar):", Qa[c], Qb[c], Qc[c]);
          }

          var t = [];
          for (var i = 63; i < data['Milliseconds'].length; i += 128) {
            t.push(data['Milliseconds'][i]);
          }
          // console.log(data['Milliseconds']);
          // console.log(t);

          // TODO probably doesn't exactly line up?
          //      need to make 2048 points, mostly null
          // duplicate first sample
          t.unshift(t[0]);
          Pa.unshift(null);
          Pb.unshift(null);
          Pc.unshift(null);
          Qa.unshift(null);
          Qb.unshift(null);
          Qc.unshift(null);

          con.createEventPowerPlot("P", t, Pa, Pb, Pc, data["two_part"]);
          con.createEventPowerPlot("Q", t, Qa, Qb, Qc, data["two_part"]);
        }
      });
    }
    else {
      var chartWaveformV = $('#container-waveform-V').highcharts();
      if (chartWaveformV) {
        chartWaveformV.destroy();
      }
      var chartWaveformI = $('#container-waveform-I').highcharts();
      if (chartWaveformI) {
        chartWaveformI.destroy();
      }
      var chartWaveformP = $('#container-waveform-P').highcharts();
      if (chartWaveformP) {
        chartWaveformP.destroy();
      }
      var chartP = $('#container-P').highcharts();
      if (chartP) {
        chartP.destroy();
      }
      var chartQ = $('#container-Q').highcharts();
      if (chartQ) {
        chartQ.destroy();
      }
    }
  },
  updateEvents: function() {
    // clear all existing event series
    var chart = $("#container").highcharts();
    if (chart) {
      for (var i = chart.series.length - 1; i >= 0; i--) {
        if (chart.series[i].type == "scatter") {
          chart.series[i].remove(false);
        }
      }

      var supported = this.get("plotTypes").objectAt(this.get("plotType")).supportsEvents;
      if (supported && this.get("showEvents")) {
        // set new event series
        Ember.$.getJSON("events/" + this.get("monitor").monitor_name_index).then(function(data) {
          var chart = $("#container").highcharts();
          if (chart) {
            // loop through eventTypes array, for consistent order in legend
            Ember.$.each(this.get("eventTypes"), function(id, eventType) {
              if (eventType.label in data) {
                var plotData = [];
                data[eventType.label].forEach(function(d) {
                  plotData.push({x: d.t, y: eventType.y, duration_ms: d.duration_ms});
                });
                var options = {
                  point: {
                    events: {
                      click: function () {
                        if (this.duration_ms > 0.0) {
                          var timestamp = this.x / 1000;
                          var con = window.App.__container__.lookup('controller:index');
                          con.set("eventWaveformTime", timestamp);
                          con.createEventWaveforms();
                        }
                      }
                    }
                  },
                  type: "scatter",
                  yAxis: 1,
                  name: eventType.name,
                  data: plotData,
                  color: eventType.plotColor,
                  marker: {
                    enabled: true,
                    radius: 4,
                    symbol: eventType.markerSymbol
                  },
                  enableMouseTracking: true,
                  cursor: 'pointer',
                  stickyTracking: false,
                  tooltip: {
                    enabled: true,
                    headerFormat: "<b>{series.name}</b><br>",
                    valueDecimals: 1,
                    hideDelay: 0,
                    pointFormatter: function() {
                      var con = window.App.__container__.lookup('controller:index');
                      var html = eventType.condition + "<br>" + Highcharts.dateFormat("%H:%M, %a %e %B %Y", new Date(this.x));

                      if (this.duration_ms > 0.0) {
                        html += "<br>" + con.eventDurationFormatter(this.duration_ms) + " duration";
                      }

                      return html;
                    }
                  },
                  states: {
                    hover: {
                      enabled: true,
                      lineWidthPlus: 0
                    }
                  }
                };
                chart.addSeries(options, false, false);
              }
            }.bind(this));
            chart.redraw();
          }
        }.bind(this));

        this.createEventWaveforms();
      }
      else {
        this.set("eventWaveformTime", null);

        chart.redraw();

        var chartWaveformV = $('#container-waveform-V').highcharts();
        if (chartWaveformV) {
          chartWaveformV.destroy();
        }
        var chartWaveformI = $('#container-waveform-I').highcharts();
        if (chartWaveformI) {
          chartWaveformI.destroy();
        }
        var chartWaveformP = $('#container-waveform-P').highcharts();
        if (chartWaveformP) {
          chartWaveformP.destroy();
        }
        var chartP = $('#container-P').highcharts();
        if (chartP) {
          chartP.destroy();
        }
        var chartQ = $('#container-Q').highcharts();
        if (chartQ) {
          chartQ.destroy();
        }
      }
    }
  }.observes("showEvents"),

  // plotting functions
  createPlotAverage: function(yAxisLabel, data) {
    var plotData = [], ranges = [];
    data.forEach(function(d) {
      plotData.push([d[0], d[1]]);
      ranges.push([d[0], d[2], d[3]]);
    });

    var chart = $('#container').highcharts();
    if (chart && !this.get("isNewPlotType")) {
      chart.yAxis[0].setTitle({text: yAxisLabel}, false);
      chart.series[0].setData(plotData, false);
      chart.series[1].setData(ranges, false);
      chart.redraw();
    }
    else {
      var options = {
        chart: {
          animation: false,
          zoomType: 'x',
          marginLeft: 65,
          marginRight: 30,
        },
        title: {
          text: ''
        },
        yAxis: [{
          min: (this.get("forceYAxisZero") ? 0.0 : null),
          title: {
            text: yAxisLabel
          },
          plotBands: null
        }, {
          min: 0,
          max: 80,
          tickInterval: 10,
          title: {
            text: null
          }
        }],
        tooltip: {
          enabled: true,
          valueDecimals: 1,
          hideDelay: 0
        },
        legend: {
          enabled: true
        },
        xAxis: {
          type: 'datetime',
          min: this.get("extremeFromDate").getTime(),
          max: this.get("extremeToDate").getTime(),
          title: {
            text: 'Time'
          },
          dateTimeLabelFormats: {
            day: '%a %e %b',
            week: '%a %e %b',
            month: '%b %Y'
          },
          events: {
            afterSetExtremes: function(e) {
              var con = window.App.__container__.lookup('controller:index');
              con.afterSetExtremes(e);
            },
            setExtremes: function (e) {
              var con = window.App.__container__.lookup('controller:index');
              con.setExtremes(e);
            }
          },
          plotLines: [{
            color: '#C0C0C0',
            value: Date.UTC(2013, 0, 1),
            width: '1'
          }, {
            color: '#C0C0C0',
            value: Date.UTC(2014, 0, 1),
            width: '1'
          }, {
            color: '#C0C0C0',
            value: Date.UTC(2015, 0, 1),
            width: '1'
          }]
        },
        series: [{
          name: 'Average',
          data: plotData,
          marker: {
            enabled: this.get("SHOW_POINT_MARKER"),
            radius: 1,
            states: {
              hover: {
                enabled: this.get("SHOW_POINT_MARKER")
              }
            }
          },
          zIndex: 1
        }, {
          name: 'Min-max range',
          data: ranges,
          type: 'arearange',
          lineWidth: 0,
          linkedTo: ':previous',
          color: 'rgba(124,181,236,0.3)',
          fillOpacity: 0.3,
          zIndex: 0,
          enableMouseTracking: false,
          showInLegend: true
        }],
        plotOptions: {
          series: {
            enableMouseTracking: this.get("SHOW_POINT_MARKER"),
            states: {
              hover: {
                enabled: true,
                lineWidthPlus: 0
              }
            },
            animation: false
          }
        },
        credits: false
      };

      $('#container').highcharts(options);
      if (!this.get("showHistogram")) {
        // if histogram shown, keep this flag set
        this.set("isNewPlotType", false);
      }
    }

    this.checkPlotZoom();
  },
  createPlotThreePhase: function(yAxisLabel, data) {
    var A = [], B = [], C = [], N = null;
    var hasNeutral = this.get("hasNeutral");
    // console.log("hasNeutral:", hasNeutral);
    if (hasNeutral) {
      N = [];
    }
    data.forEach(function(d) {
      A.push([d[0], d[1]]);
      B.push([d[0], d[2]]);
      C.push([d[0], d[3]]);
      if (hasNeutral && d.length == 5) {
        N.push([d[0], d[4]]);
      }
    });
    // console.log("N:", N);

    var chart = $('#container').highcharts();
    if (chart && !this.get("isNewPlotType")) {
      chart.yAxis[0].setTitle({text: yAxisLabel}, false);
      chart.series[0].setData(A, false);
      chart.series[1].setData(B, false);
      chart.series[2].setData(C, false);

      if (this.get("hasNeutral") && N) {
        if (!this.get("showNeutral")) {
          chart.series[3].setVisible(true, true);   // unnecessary redraw() due to bug in Highcharts
        }
        chart.series[3].setData(N, false, false, false);
        if (!this.get("showNeutral")) {
          chart.series[3].setVisible(false, false);
        }
      }
      else {
        chart.series[3].setData(null, false);
      }

      if (this.get("hasNeutral") && this.get("showNeutral")) {
        chart.series[3].setVisible(true, false);
      }
      else {
        chart.series[3].setVisible(false, false);
      }

      // console.log("chart.series[3].data.length:", chart.series[3].data.length);
      chart.redraw();
    }
    else {
      var options = {
        chart: {
          animation: false,
          zoomType: 'x',
          marginLeft: 65,
          marginRight: 30
        },
        title: {
          text: ''
        },
        yAxis: [{
          min: (this.get("forceYAxisZero") ? 0.0 : null),
          title: {
              text: yAxisLabel
          },
          plotBands: null
        }, {
          min: 0,
          max: 80,
          title: {
            text: null
          }
        }],
        tooltip: {
          enabled: this.get("SHOW_TOOLTIPS"),
          shared: true,
          valueDecimals: 1,
          hideDelay: 0
        },
        xAxis: {
          type: 'datetime',
          min: this.get("extremeFromDate").getTime(),
          max: this.get("extremeToDate").getTime(),
          dateTimeLabelFormats: {
            day: '%a %e %b',
            week: '%a %e %b',
            month: '%b %Y'
          },
          events: {
            afterSetExtremes: function(e) {
              var con = window.App.__container__.lookup('controller:index');
              con.afterSetExtremes(e);
            },
            setExtremes: function (e) {
              var con = window.App.__container__.lookup('controller:index');
              con.setExtremes(e);
            }
          },
          plotLines: [{
            color: '#C0C0C0',
            value: Date.UTC(2013, 0, 1),
            width: '1'
          }, {
            color: '#C0C0C0',
            value: Date.UTC(2014, 0, 1),
            width: '1'
          }, {
            color: '#C0C0C0',
            value: Date.UTC(2015, 0, 1),
            width: '1'
          }]
        },
        series: [{
          name: 'Phase A',
          data: A,
          color: 'rgba(180, 33, 38, 0.8)',
          marker: {
              enabled: this.get("SHOW_POINT_MARKER"),
              radius: 1,
              states: {
                hover: {
                  enabled: this.get("SHOW_POINT_MARKER")
                }
              }
          }
        }, {
          name: 'Phase B',
          color: 'rgba(222, 215, 20, 0.8)',
          data: B,
          marker: {
              enabled: this.get("SHOW_POINT_MARKER"),
              radius: 1,
              states: {
                hover: {
                  enabled: this.get("SHOW_POINT_MARKER")
                }
              }
          }
        }, {
          name: 'Phase C',
          color: 'rgba(36, 78, 198, 0.8)',
          data: C,
          marker: {
              enabled: this.get("SHOW_POINT_MARKER"),
              radius: 1,
              states: {
                hover: {
                  enabled: this.get("SHOW_POINT_MARKER")
                }
              }
          }
        }, {
          name: 'Neutral',
          visible: this.get("showNeutral"),
          color: 'rgba(40, 40, 40, 0.8)',
          data: N,
          marker: {
            enabled: this.get("SHOW_POINT_MARKER"),
            radius: 1,
            states: {
              hover: {
                enabled: this.get("SHOW_POINT_MARKER")
              }
            }
          },
          events: {
            legendItemClick: function(e) {
              var con = window.App.__container__.lookup('controller:index');
              con.set("showNeutral", !con.get("showNeutral"));
            }
          }
        }],
        plotOptions: {
          series: {
            enableMouseTracking: this.get("SHOW_POINT_MARKER"),
            states: {
              hover: {
                enabled: this.get("SHOW_POINT_MARKER"),
                lineWidthPlus: 0
              }
            },
            animation: false
          }
        },
        credits: false
      };
      $('#container').highcharts(options);

      if (!this.get("showHistogram")) {
        // if histogram shown, keep this flag set
        this.set("isNewPlotType", false);
      }
      // var chart = $('#container').highcharts();
      // chart.series[3].setVisible(true, false);
      // chart.series[3].setVisible(false, false);
      // console.log("chart.series[3].data.length:", chart.series[3].data.length);
    }
    
    this.checkPlotZoom();
  },
  createPlotDayPolar: function(yAxisLabel, data, isThreePhase) {
    var A = [], B = [], C = [], N = null;
    var phaseAColour = null;
    if (isThreePhase) {
      phaseAColour = 'rgba(180, 33, 38, 0.8)';
      if (data != null && data[0] != null && data[0].length == 5) {
        N = [];
      }
      data.forEach(function(d) {
        A.push([d[0], d[1]]);
        B.push([d[0], d[2]]);
        C.push([d[0], d[3]]);
        if (d.length == 5) {
          N.push([d[0], d[4]]);
        }
      });
    }
    else {
      B = null, C = null, N = null;
      data.forEach(function(d) {
        A.push([d[0], d[1]]);
      });
    }

    var chart = $('#container').highcharts();
    if (chart && !this.get("isNewPlotType")) {
      chart.yAxis[0].setTitle({text: yAxisLabel}, false);
      chart.series[0].setData(A, false);
      chart.series[1].setData(B, false);
      chart.series[2].setData(C, false);
      if (this.get("hasNeutral") && N) {
        if (!this.get("showNeutral")) {
          chart.series[3].setVisible(true, true);   // unnecessary redraw() due to bug in Highcharts
        }
        chart.series[3].setData(N, false, false, false, false);
        if (!this.get("showNeutral")) {
          chart.series[3].setVisible(false, false);
        }
      }
      else {
        chart.series[3].setData(null, false);
      }

      if (this.get("hasNeutral") && this.get("showNeutral")) {
        chart.series[3].setVisible(true, false);
      }
      else {
        chart.series[3].setVisible(false, false);
      }
      chart.redraw();
    }
    else {
      var options = {
        chart: {
          animation: false,
          polar: true
        },
        title: {
          text: ''
        },
        yAxis: {
          min: (this.get("forceYAxisZero") ? 0.0 : null),
          title: {
              text: yAxisLabel
          },
          plotBands: null
        },
        tooltip: {
          enabled: this.get("SHOW_TOOLTIPS"),
          shared: true,
          valueDecimals: 1,
          hideDelay: 0
        },
        xAxis: {
          type: 'datetime',
          dateTimeLabelFormats: {
            day: '%a %e %b %Y',
            week: '%a %e %b',
            month: '%b %Y'
          }
        },
        series: [{
          name: 'Phase A',
          data: A,
          color: phaseAColour,
          marker: {
              enabled: false,
              radius: 1,
              states: {
                hover: {
                  enabled: false
                }
              }
          }
        }, {
          name: 'Phase B',
          visible: isThreePhase,
          color: 'rgba(222, 215, 20, 0.8)',
          data: B,
          marker: {
              enabled: false,
              radius: 1,
              states: {
                hover: {
                  enabled: false
                }
              }
          }
        }, {
          name: 'Phase C',
          visible: isThreePhase,
          color: 'rgba(36, 78, 198, 0.8)',
          data: C,
          marker: {
              enabled: false,
              radius: 1,
              states: {
                hover: {
                  enabled: false
                }
              }
          }
        }, {
          name: 'Neutral',
          visible: this.get("showNeutral"),
          color: 'rgba(40, 40, 40, 0.8)',
          data: N,
          marker: {
            enabled: false,
            radius: 1,
            states: {
              hover: {
                enabled: false
              }
            }
          },
          events: {
            legendItemClick: function(e) {
              var con = window.App.__container__.lookup('controller:index');
              con.set("showNeutral", !con.get("showNeutral"));
            }
          }
        }],
        plotOptions: {
          series: {
            enableMouseTracking: this.get("SHOW_POINT_MARKER"),
            states: {
              hover: {
                enabled: false
              }
            }
          }
        },
        credits: false
      };

      $('#container').highcharts(options);
      if (!this.get("showHistogram")) {
        // if histogram shown, keep this flag set
        this.set("isNewPlotType", false);
      }
    }
  },
  createPlotHeatMap: function(yAxisLabel, data, quantity, units) {
    var options = {
      chart: {
        type: 'heatmap',
        marginLeft: 75,
        marginRight: 30
      },
      title: {
        text: ''
      },
      subtitle: {
        text: ''
      },
      tooltip: {
        enabled: this.get("SHOW_TOOLTIPS"),
        backgroundColor: null,
        borderWidth: 0,
        distance: 10,
        shadow: false,
        useHTML: true,
        style: {
          padding: 0,
          color: 'black'
        },
        hideDelay: 0
      },
      xAxis: {
        type: "datetime",
        title: {
          text: "Days"
        },
        dateTimeLabelFormats: {
          day: '%a %e %b %Y',
          week: '%a %e %b',
          month: '%b %Y'
        },
        min: this.get("extremeFromDate").getTime(),
        max: this.get("extremeToDate").getTime()
      },
      yAxis: {
        title: {
          text: "Time of day"
        },
        labels: {
          format: "{value}:00#"
        },
        minPadding: 0,
        maxPadding: 0,
        startOnTick: false,
        endOnTick: false,
        tickPositions: [0, 6, 12, 18, 24],
        tickWidth: 1,
        min: 0,
        max: 23,
        reversed: true
      },
      colorAxis: {
        stops: [
          [0, '#3060cf'],
          [0.5, '#fffbbc'],
          [0.9, '#c4463a'],
          [1, '#c4463a']
        ],
        startOnTick: false,
        endOnTick: false,
        labels: {
          format: '{value} ' + units
        }
      },
      series: [{
        data: data,
        borderWidth: 0,
        nullColor: '#EFEFEF',
        colsize: 24 * 36e5, // one day
        tooltip: {
          headerFormat: quantity + ' (average)<br/>',
          pointFormat: '{point.x:%e %b %Y} {point.y}:00: <b>{point.value:.1f} ' + units + '</b>'
        },
        turboThreshold: Number.MAX_VALUE  // needed to cope with large number of data points
      }],
      credits: false
    };

    $('#container').highcharts(options);
  },
  createPlotWaveform: function(yAxisLabel, data) {
    var chart = $('#container').highcharts();
    if (chart && !this.get("isNewPlotType")) {
      chart.yAxis[0].setTitle({text: yAxisLabel}, false);
      chart.series[0].setData(data[0], false);
      chart.series[1].setData(data[1], false);
      chart.series[2].setData(data[2], false);
      chart.redraw();
    }
    else {
      var pointInterval = 40.0 / 400.0; // = time interval (ms) / steps
      var options = {
        chart: {
          animation: false,
          marginLeft: 80,
          marginRight: 30
        },
        title: {
          text: Highcharts.dateFormat("%H:%M, %a %e %B %Y", this.get("shownFromDate").getTime())
        },
        yAxis: {
          title: {
              text: yAxisLabel
          },
          plotBands: null
        },
        tooltip: {
          enabled: this.get("SHOW_TOOLTIPS"),
          headerFormat: '<span style="font-size: 10px">{point.key:.1f} ms</span><br/>',
          shared: true,
          valueDecimals: 1,
          hideDelay: 0
        },
        xAxis: {
          title: {
            text: 'Time (ms)'
          },
          plotLines: [{
            color: '#C0C0C0',
            value: 20.0,
            width: '1'
          }]
        },
        series: [{
          name: 'Phase A',
          pointStart: 0,
          pointInterval: pointInterval,
          data: data[0],
          color: 'rgba(180, 33, 38, 0.8)',
          marker: {
              enabled: this.get("SHOW_POINT_MARKER"),
              radius: 1,
              states: {
                hover: {
                  enabled: this.get("SHOW_POINT_MARKER")
                }
              }
          }
        }, {
          name: 'Phase B',
          pointStart: 0,
          pointInterval: pointInterval,
          color: 'rgba(222, 215, 20, 0.8)',
          data: data[1],
          marker: {
              enabled: this.get("SHOW_POINT_MARKER"),
              radius: 1,
              states: {
                hover: {
                  enabled: this.get("SHOW_POINT_MARKER")
                }
              }
          }
        }, {
          name: 'Phase C',
          pointStart: 0,
          pointInterval: pointInterval,
          color: 'rgba(36, 78, 198, 0.8)',
          data: data[2],
          marker: {
              enabled: this.get("SHOW_POINT_MARKER"),
              radius: 1,
              states: {
                hover: {
                  enabled: this.get("SHOW_POINT_MARKER")
                }
              }
          }
        }],
        plotOptions: {
          series: {
            enableMouseTracking: this.get("SHOW_POINT_MARKER"),
            states: {
              hover: {
                enabled: this.get("SHOW_POINT_MARKER"),
                lineWidthPlus: 0
              }
            },
            animation: false
          }
        },
        credits: false
      };

      $('#container').highcharts(options);
    }

    chart = $('#container').highcharts();
    if (chart && data[0].length == 0) {
      chart.setTitle({text: 'No data available'});
    }
  },
  createPlotHarmonics: function(yAxisLabel, data) {
    var chart = $('#container').highcharts();
    if (chart && !this.get("isNewPlotType")) {
      chart.yAxis[0].setTitle({text: yAxisLabel}, false);
      chart.series[0].setData(data[1], false);
      chart.series[1].setData(data[2], false);
      chart.series[2].setData(data[3], false);
      chart.redraw();
    }
    else {
      var options = {
        chart: {
          type: 'column',
          animation: false,
          marginLeft: 80,
          marginRight: 30
        },
        title: {
          text: Highcharts.dateFormat("%H:%M, %a %e %B %Y", this.get("shownFromDate").getTime())
        },
        yAxis: {
          title: {
              text: yAxisLabel
          },
          plotBands: null
        },
        tooltip: {
          enabled: this.get("SHOW_TOOLTIPS"),
          headerFormat: (this.get("showInterharmonics")) ? '<span style="font-size: 10px">{point.key} interharmonic</span><br/>' : '<span style="font-size: 10px">{point.key} harmonic</span><br/>',
          shared: true,
          valueDecimals: 2,
          hideDelay: 0
        },
        xAxis: {
          categories: data[0],
          title: {
            text: (this.get("showInterharmonics")) ? 'Interharmonic number' : 'Harmonic number'
          }
        },
        series: [{
          name: 'Phase A',
          data: data[1],
          color: 'rgba(180, 33, 38, 0.8)',
          marker: {
              enabled: this.get("SHOW_POINT_MARKER"),
              radius: 1,
              states: {
                hover: {
                  enabled: this.get("SHOW_POINT_MARKER")
                }
              }
          }
        }, {
          name: 'Phase B',
          color: 'rgba(222, 215, 20, 0.8)',
          data: data[2],
          marker: {
              enabled: this.get("SHOW_POINT_MARKER"),
              radius: 1,
              states: {
                hover: {
                  enabled: this.get("SHOW_POINT_MARKER")
                }
              }
          }
        }, {
          name: 'Phase C',
          color: 'rgba(36, 78, 198, 0.8)',
          data: data[3],
          marker: {
              enabled: this.get("SHOW_POINT_MARKER"),
              radius: 1,
              states: {
                hover: {
                  enabled: this.get("SHOW_POINT_MARKER")
                }
              }
          }
        }],
        plotOptions: {
          series: {
            enableMouseTracking: this.get("SHOW_POINT_MARKER"),
            states: {
              hover: {
                enabled: this.get("SHOW_POINT_MARKER"),
                lineWidthPlus: 0
              }
            },
            animation: false
          }
        },
        credits: false
      };

      $('#container').highcharts(options);
    }

    chart = $('#container').highcharts();
    if (chart && data.length == 0) {
      chart.setTitle({text: 'No data available'});
    }
  },
  createPlotHarmonicsTrends: function(yAxisLabel, data, harmonicNumbers) {
    var allSeries = [];
    for (var i = 1; i < data.length; i++) {
      var series = {
        name: harmonicNumbers[i - 1].nth(),
        data: [],
        marker: {
            enabled: this.get("SHOW_POINT_MARKER"),
            radius: 1,
            states: {
              hover: {
                enabled: this.get("SHOW_POINT_MARKER")
              }
            }
        }
      };

      if (harmonicNumbers[i - 1] == 1 && !this.get("showFundamental")) {
        series.visible = false;
      }
      if (harmonicNumbers[i - 1] == 1) {
        series.events = {}
        series.events.legendItemClick = function(e) {
          this.set("showFundamental", !this.get("showFundamental"));
        };
      }

      for (var j = 0; j < data[i].length; j++) {
        series.data.push([data[0][j], data[i][j]]);
      }
      allSeries.push(series);
    }

    var chart = $('#container').highcharts();
    if (chart && !this.get("isNewPlotType")) {
      chart.yAxis[0].setTitle({text: yAxisLabel}, false);
      for (var i = 0; i < allSeries.length; i++) {
        if (chart.series[i]) {
          if (!this.get("showFundamental") && i == 0) {
            chart.series[0].setVisible(true, true);   // unnecessary redraw() due to bug in Highcharts
          }
          chart.series[i].setData(allSeries[i].data, false);
          if (!this.get("showFundamental") && i == 0) {
            chart.series[0].setVisible(false, false);
          }
        }
      }

      chart.redraw();
      chart.hideLoading();
    }
    else {
      var options = {
        chart: {
          animation: false,
          zoomType: 'x',
          marginLeft: 80,
          marginRight: 30
        },
        title: {
          text: ''
        },
        yAxis: [{
          min: 0.0,
          title: {
              text: yAxisLabel
          },
          plotBands: null
        }, {
          min: 0,
          max: 80,
          tickInterval: 10,
          title: {
            text: null
            }
        }],
        tooltip: {
          enabled: true,
          shared: true,
          valueDecimals: 2,
          hideDelay: 0
        },
        xAxis: {
          type: 'datetime',
          min: this.get("extremeFromDate").getTime(),
          max: this.get("extremeToDate").getTime(),
          dateTimeLabelFormats: {
            day: '%a %e %b',
            week: '%a %e %b',
            month: '%b %Y'
          },
          events: {
            afterSetExtremes: function(e) {
              var con = window.App.__container__.lookup('controller:index');
              con.afterSetExtremes(e);
            },
            setExtremes: function (e) {
              var con = window.App.__container__.lookup('controller:index');
              con.setExtremes(e);
            }
          },
          plotLines: [{
            color: '#C0C0C0',
            value: Date.UTC(2013, 0, 1),
            width: '1'
          }, {
            color: '#C0C0C0',
            value: Date.UTC(2014, 0, 1),
            width: '1'
          }, {
            color: '#C0C0C0',
            value: Date.UTC(2015, 0, 1),
            width: '1'
          }]
        },
        series: allSeries,
        plotOptions: {
          series: {
            enableMouseTracking: this.get("SHOW_POINT_MARKER"),
            states: {
              hover: {
                enabled: this.get("SHOW_POINT_MARKER"),
                lineWidthPlus: 0
              }
            },
            animation: false
          }
        },
        credits: false
      };

      $('#container').highcharts(options);
      if (!this.get("showHistogram")) {
        // if histogram shown, keep this flag set
        this.set("isNewPlotType", false);
      }
    }

    chart = $('#container').highcharts();
    if (chart && data.length == 0) {
      chart.setTitle({text: 'No data available'});
      for (var i = 0; i < chart.series.length; i++) {
        chart.series[i].setData(null, false);
      }
      chart.redraw();
    }
    else {
      chart.setTitle({text: null});
    }

    this.checkPlotZoom();
  },
  createEventWaveformPlot: function(plotType, t, A, B, C, N, isSplit) {
    var yAxisLabel = "Voltage (V)";
    var neutralLabel = "Neutral-earth";
    var neutralState = false;
    var timeLabelY = 300;

    if (plotType == "I") {
      yAxisLabel = "Current (A)";
      neutralLabel = "Neutral";
      neutralState = true;
      timeLabelY = 500;
    }
    else if (plotType == "P") {
      yAxisLabel = "Instantaneous power (kW)";
      neutralLabel = "Neutral";
      neutralState = false;
      timeLabelY = 500;
    }
    var plotLines = null;
    var labelsData = [];
    if (isSplit) {
      plotLines = [{
        id: "1023",
        color: "#000000",
        value: 1023,
        width: 2,
        zIndex: 5
      }, {
        id: "1024",
        color: "#000000",
        value: 1024,
        width: 2,
        zIndex: 5
      }];

      labelsData = [{x: 0, y: timeLabelY, name: "0 ms"}, {x: 1024, y: timeLabelY, name: this.eventDurationFormatter(t[1024])}];
    }

    var chart = $("#container-waveform-" + plotType).highcharts();
    if (chart) {
      chart.yAxis[0].setTitle({text: yAxisLabel}, false);

      chart.series[0].setData(A, false);
      chart.series[1].setData(B, false);
      chart.series[2].setData(C, false);
      if (N) {
        chart.series[3].setData(N, false);
      }
      chart.series[4].setData(labelsData, false);

      chart.xAxis[0].removePlotLine("1023");
      chart.xAxis[0].removePlotLine("1024");

      if (isSplit) {
        chart.xAxis[0].addPlotLine(plotLines[0]);
        chart.xAxis[0].addPlotLine(plotLines[1]);
      }
      chart.redraw();
    }
    else {
      var options = {
        chart: {
          animation: false,
          zoomType: 'x',
          marginLeft: 70,
          marginRight: 30,
          height: 200
        },
        title: {
          text: ''
        },
        yAxis: {
          title: {
              text: yAxisLabel
          },
          plotBands: null
        },
        tooltip: {
          enabled: false
        },
        xAxis: {
          labels: {
            enabled: false
          },
          minorTickLength: 0,
          tickLength: 0,
          plotLines: plotLines,
          events: {
            afterSetExtremes: function(e) {
              var con = window.App.__container__.lookup('controller:index');

              if (!con.get("skipCallback")) {
                var plotNames = ["#container-waveform-V", "#container-waveform-P"];
                if (plotType == "V") {
                  plotNames = ["#container-waveform-I", "#container-waveform-P"];
                }
                else if (plotType == "P") {
                  plotNames = ["#container-waveform-V", "#container-waveform-I"];
                }

                for (var i = 0; i < plotNames.length; i++) {
                  var chartWaveform = $(plotNames[i]).highcharts();
                  if (chartWaveform) {
                    var zoomEvent = {
                      xAxis: [{
                        axis: chartWaveform.xAxis[0],
                        min: e.min,
                        max: e.max
                      }],
                      yAxis: []
                    };
                    con.set("skipCallback", true);
                    chartWaveform.zoom(zoomEvent);
                  }
                }
              }
              else {
                con.set("skipCallback", false);
              }
            }
          }
        },
        series: [{
          name: 'Phase A',
          data: A,
          color: 'rgba(180, 33, 38, 0.8)',
          marker: {
              enabled: false,
              radius: 1,
              states: {
                hover: {
                  enabled: false
                }
              }
          },
          pointStart: 0,
          pointInterval: 1
        }, {
          name: 'Phase B',
          color: 'rgba(222, 215, 20, 0.8)',
          data: B,
          marker: {
              enabled: false,
              radius: 1,
              states: {
                hover: {
                  enabled: false
                }
              }
          },
          pointStart: 0,
          pointInterval: 1
        }, {
          name: 'Phase C',
          color: 'rgba(36, 78, 198, 0.8)',
          data: C,
          marker: {
              enabled: false,
              radius: 1,
              states: {
                hover: {
                  enabled: false
                }
              }
          },
          pointStart: 0,
          pointInterval: 1
        }, {
          name: neutralLabel,
          visible: neutralState,
          color: 'rgba(40, 40, 40, 0.8)',
          data: N,
          marker: {
            enabled: false,
            radius: 1,
            states: {
              hover: {
                enabled: false
              }
            }
          },
          pointStart: 0,
          pointInterval: 1
        }, {
          name: "",
          type: "scatter",
          color: 'rgba(0, 0, 0, 1.0)',
          data: labelsData,
          showInLegend: false,
          marker: {
            enabled: false,
            radius: 1,
            states: {
              hover: {
                enabled: false
              }
            }
          },
          dataLabels: {
            enabled: true,
            format: "{point.name}",
            align: "left"
          },
          pointStart: 0,
          pointInterval: 1
        }],
        plotOptions: {
          series: {
            enableMouseTracking: this.get("SHOW_POINT_MARKER"),
            states: {
              hover: {
                enabled: false,
                lineWidthPlus: 0
              }
            },
            animation: false
          }
        },
        credits: false
      };
      $("#container-waveform-" + plotType).highcharts(options);
    }
  },
  createEventPowerPlot: function(plotType, t, A, B, C, isSplit) {
    var yAxisLabel = "Reactive power (kvar)";
    var timeLabelY = 300;

    if (plotType == "P") {
      yAxisLabel = "Real power (kW)";
      timeLabelY = 500;
    }
    var plotLines = null;
    var labelsData = [];
    if (isSplit) {
      plotLines = [{
        id: "1023",
        color: "#000000",
        value: 1023,
        width: 2,
        zIndex: 5
      }, {
        id: "1024",
        color: "#000000",
        value: 1024,
        width: 2,
        zIndex: 5
      }];

      labelsData = [{x: 0, y: timeLabelY, name: "0 ms"}, {x: 1024, y: timeLabelY, name: this.eventDurationFormatter(t[1024])}];
    }

    var chart = $("#container-" + plotType).highcharts();
    if (chart) {
      chart.yAxis[0].setTitle({text: yAxisLabel}, false);

      chart.series[0].setData(A, false);
      chart.series[1].setData(B, false);
      chart.series[2].setData(C, false);
      chart.series[3].setData(labelsData, false);

      chart.xAxis[0].removePlotLine("1023");
      chart.xAxis[0].removePlotLine("1024");

      if (isSplit) {
        chart.xAxis[0].addPlotLine(plotLines[0]);
        chart.xAxis[0].addPlotLine(plotLines[1]);
      }
      chart.redraw();
    }
    else {
      var options = {
        chart: {
          type: 'spline',
          animation: true,
          zoomType: 'x',
          marginLeft: 70,
          marginRight: 30,
          height: 200
        },
        title: {
          text: ''
        },
        yAxis: {
          title: {
              text: yAxisLabel
          },
          plotBands: null
        },
        tooltip: {
          enabled: true
        },
        xAxis: {
          labels: {
            enabled: true
          },
          minorTickLength: 0,
          tickLength: 0,
          plotLines: plotLines,
          events: {
            afterSetExtremes: function(e) {
              // TODO

              // var con = window.App.__container__.lookup('controller:index');

              // if (!con.get("skipCallback")) {
              //   var plotNames = ["#container-waveform-V", "#container-waveform-P"];
              //   if (plotType == "V") {
              //     plotNames = ["#container-waveform-I", "#container-waveform-P"];
              //   }
              //   else if (plotType == "P") {
              //     plotNames = ["#container-waveform-V", "#container-waveform-I"];
              //   }

              //   for (var i = 0; i < plotNames.length; i++) {
              //     var chartWaveform = $(plotNames[i]).highcharts();
              //     if (chartWaveform) {
              //       var zoomEvent = {
              //         xAxis: [{
              //           axis: chartWaveform.xAxis[0],
              //           min: e.min,
              //           max: e.max
              //         }],
              //         yAxis: []
              //       };
              //       con.set("skipCallback", true);
              //       chartWaveform.zoom(zoomEvent);
              //     }
              //   }
              // }
              // else {
              //   con.set("skipCallback", false);
              // }
            }
          }
        },
        series: [{
          name: 'Phase A',
          data: A,
          color: 'rgba(180, 33, 38, 0.8)',
          marker: {
              enabled: true,
              radius: 1,
              states: {
                hover: {
                  enabled: true
                }
              }
          },
          pointStart: 0,
          pointInterval: 1
        }, {
          name: 'Phase B',
          color: 'rgba(222, 215, 20, 0.8)',
          data: B,
          marker: {
              enabled: true,
              radius: 1,
              states: {
                hover: {
                  enabled: true
                }
              }
          },
          pointStart: 0,
          pointInterval: 1
        }, {
          name: 'Phase C',
          color: 'rgba(36, 78, 198, 0.8)',
          data: C,
          marker: {
              enabled: true,
              radius: 1,
              states: {
                hover: {
                  enabled: true
                }
              }
          },
          pointStart: 0,
          pointInterval: 1
        }, {
          name: "",
          type: "scatter",
          color: 'rgba(0, 0, 0, 1.0)',
          data: labelsData,
          showInLegend: false,
          marker: {
            enabled: false,
            radius: 1,
            states: {
              hover: {
                enabled: false
              }
            }
          },
          dataLabels: {
            enabled: true,
            format: "{point.name}",
            align: "left"
          },
          pointStart: 0,
          pointInterval: 1
        }],
        plotOptions: {
          series: {
            enableMouseTracking: true,//this.get("SHOW_POINT_MARKER"),
            states: {
              hover: {
                enabled: true,
                lineWidthPlus: 0
              }
            },
            animation: true
          }
        },
        credits: false
      };
      $("#container-" + plotType).highcharts(options);
    }
  },

  // plot helper functions and callbacks
  checkPlotZoom: function() {
    var chart = $('#container').highcharts();

    if (chart && (this.get("shownFromDate").getTime() != this.get("extremeFromDate").getTime() || this.get("shownToDate").getTime() != this.get("extremeToDate").getTime())) {
      var zoomEvent = {
        xAxis: [{
          axis: chart.xAxis[0],
          min: this.get("shownFromDate").getTime(),
          max: this.get("shownToDate").getTime()
        }],
        yAxis: []
      };
      this.set("skipCallback", true);
      chart.zoom(zoomEvent);
    }
  },
  setExtremes: function(e) {
    var isReset = false;

    if (e.min == null && e.max == null) {
      isReset = true;
      this.set("skipCallback", false);
    }
    else {
      isReset = false;
    }
    this.set("isReset", isReset);
  },
  afterSetExtremes: function(e) {
    if (!this.get("skipCallback")) {
      // load new data depending on the selected min and max date range
      var chart = $('#container').highcharts();
      var min = new Date(e.min);
      var max = new Date(e.max);

      if (!this.get("isReset")) {
        this.set("shownFromDate", min);
        this.set("shownToDate", max);
        this.set("skipCallback", true);
      }
      else {
        this.set("shownFromDate", this.get("extremeFromDate"));
        this.set("shownToDate", this.get("extremeToDate"));
        this.set("isReset", false);
      }

      this.update();
    }
    else {
     this.set("skipCallback", false);
    }
  }
});