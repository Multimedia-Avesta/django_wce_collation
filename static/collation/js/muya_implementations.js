/*jshint esversion: 6 */

var LOCAL = (function () {
  "use strict";
  return {

    RDVisible: false,
    RDTVisible: false,

    prepareDisplayString: function (string) {
      return string;
    },

    prepareNormalisedString: function (string) {
      return string;
    },

    project_witness_sort: function(witnesses) {
      return witnesses.sort(LOCAL.sort_witnesses);
    },

    //used before moving to order readings to make sure that a decision has been made on all top line overlapped readings
    are_no_duplicate_statuses: function() {
      var i, j;
      for (i = 0; i < CL.data.apparatus.length; i += 1) {
        for (j = 0; j < CL.data.apparatus[i].readings.length; j += 1) {
          if (CL.data.apparatus[i].readings[j].hasOwnProperty('overlap_status') &&
            CL.data.apparatus[i].readings[j].overlap_status === 'duplicate') {
            return false;
          }
        }
      }
      return true;
    },

    check_om_overlap_problems: function() {
      var i, unit, j, witnesses, key, ol_unit;
      //check to see if any readings labelled 'overlapped' don't have any text in the overlapped reading
      //if they do then that needs fixing.
      for (i = 0; i < CL.data.apparatus.length; i += 1) {
        unit = CL.data.apparatus[i];
        if ('overlap_units' in unit) {
          witnesses = [];
          for (j = 0; j < unit.readings.length; j += 1) {
            if ('overlap_status' in unit.readings[j] &&
              unit.readings[j].overlap_status === 'overlapped') {
              witnesses.push.apply(witnesses, unit.readings[j].witnesses);
            }
          }
          //for each witness we've collected
          for (j = 0; j < witnesses.length; j += 1) {
            for (key in unit.overlap_units) {
              if (unit.overlap_units[key].indexOf(witnesses[j]) != -1) {
                ol_unit = CL.findOverlapUnitById(key);
                if (ol_unit.readings[1].text.length > 0) { //hard coded 1 is fine as at this stage there is only one reading and its always here
                  return true;
                }
              }
            }
          }
        }
      }
      return false;
    },

    are_no_disallowed_overlaps: function() {
      var key, main_apparatus_data, unit, i;
      main_apparatus_data = [];
      for (i = 0; i < CL.data.apparatus.length; i += 1) {
        unit = CL.data.apparatus[i];
        main_apparatus_data.push(unit.start + '-' + unit.end);
      }
      for (key in CL.data) {
        if (key.indexOf('apparatus') !== -1 && key !== 'apparatus') {
          for (i = 0; i < CL.data[key].length; i += 1) {
            unit = CL.data[key][i];
            if (main_apparatus_data.indexOf(unit.start + '-' + unit.end) !== -1) {
              return false;
            }
          }
        }
      }
      return true;
    },

    compare_witness_suffixes: function(a, b) {
      if (a[0] === '-' && b[0] === '-') {
        return a.replace('-', '') - b.replace('-', '');
      }
      if (a[0] === '*') {
        return -1;
      }
      if (b[0] === '*') {
        return 1;
      }
      return 0;
      //could do more tests here for other suffixes but this is probably enough for now
    },


    sort_witnesses: function (a, b) {
      var dig_regex, suf_regex, numberA, numberB, suffixA, suffixB;
      if ($.isPlainObject(a)) {
        a = a.hand;
      }
      if ($.isPlainObject(b)) {
        b = b.hand;
      }
      dig_regex = /\d+/;
      suf_regex = /\D+\d*/;
      //extract just the number
      if (!a.match(dig_regex)) {
        return 1;
      } if (!b.match(dig_regex)) {
        return -1;
      }
      numberA = parseInt(a.match(dig_regex)[0], 10);
      numberB = parseInt(b.match(dig_regex)[0], 10);
      //if the numbers are the same deal with the suffixes
      if (numberA === numberB) {
        if (a.match(suf_regex)) {
          suffixA = a.match(suf_regex)[0];
        } else {
          suffixA = [''];
        }
        if (b.match(suf_regex)) {
          suffixB = b.match(suf_regex)[0];
        } else {
          suffixB = [''];
        }
        return LOCAL.compare_witness_suffixes(suffixA, suffixB);
      }
      //if the numbers are not the same sort them
      return numberA - numberB;
    },

    showRitualDirections: function () {
      if (LOCAL.RDVisible === true) {
        LOCAL.RDVisible = false;
        LOCAL.RDTVisible = true;
      } else if (LOCAL.RDTVisible === true) {
        LOCAL.RDVisible = false;
        LOCAL.RDTVisible = false;
      } else {
        LOCAL.RDVisible = true;
        LOCAL.RDTVisible = false;
      }
      if (CL.stage === 'regularise') {
        RG.showVerseCollation(CL.data, CL.context, CL.container);
      } else if (CL.stage === 'set') {
        SV.showSetVariants({'container': CL.container});
      } else if (CL.stage === 'ordered') {
        OR.showOrderReadings({'container': CL.container});
      } else if (CL.stage === 'approved') {
        OR.showApprovedVersion({'container': CL.container});
      }

    },

    extractWordsForHeader: function(data) {
        var word, words = [];
        for (let i = 0; i < data.length; i += 1) {
            word = [];
            if (LOCAL.RDVisible && data[i].hasOwnProperty('rd_before')) {
                word.push(data[i].rd_before);
                word.push(' ');
            }
            if (LOCAL.RDTVisible && data[i].hasOwnProperty('rdt_before')) {
                word.push(data[i].rdt_before);
                word.push(' ');
            }
            if (data[i].hasOwnProperty('pc_before')) {
                word.push(data[i].pc_before);
            }
            if (data[i].hasOwnProperty('original')) {
                word.push(data[i].original);
            } else {
                word.push(data[i].t);
            }
            if (data[i].hasOwnProperty('pc_after')) {
                word.push(data[i].pc_after);
            }
            if (LOCAL.RDVisible && data[i].hasOwnProperty('rd_after')) {
                word.push(' ');
                word.push(data[i].rd_after);
            }
            if (LOCAL.RDTVisible && data[i].hasOwnProperty('rdt_after')) {
                word.push(' ');
                word.push(data[i].rdt_after);
            }
            if (data[i].hasOwnProperty('type')) {
                words.push([word.join(''), data[i].type]);
            } else {
                words.push([word.join(''), '']);
            }
        }
        return words;
    },
  };
}());
