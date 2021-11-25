/*jshint esversion: 6 */
ceremony = (function() {
  "use strict";

  var _addHandlers, _deleteMapping, _displayAddEditForm, _saveCeremonyMapping, _validateCeremonyMapping,
  _isValidMapping, _populateForm, _displayCeremonyEditForm, _addCeremony, _addDeleteFunctions, _saveCeremonyList;

  $(document).ready(function() {
    _addHandlers();
  });

  _addHandlers = function() {
    $('#delete_mapping_button').on('click', function() {
      var context;
      context = $("input[type='radio'][name='context']:checked").val();
      if (context === undefined) {
        return;
      }
      _deleteMapping(context);
    });
    $('#edit_mapping_button').on('click', function() {
      var context, details;
      context = $("input[type='radio'][name='context']:checked").val();
      try {
        details = document.getElementById(context).value;
        _displayAddEditForm(document.getElementById('project_id').value, 'edit', function () {
          _populateForm(context, details);
        });
      } catch (err) {
        return;
      }
    });
    $('#add_mapping_button').on('click', function() {
      _displayAddEditForm(document.getElementById('project_id').value, 'add');
    });
    $('#edit_ceremonies_button').on('click', function() {
      _displayCeremonyEditForm(document.getElementById('project_id').value);
    });
    $('#search_field').on('change', function() {
			var value;
			value = $(this)[0].value;
			$('#search_text').attr('name', value);
		});
    $('.buttonlink').on('click', function(event){
		    event.preventDefault();
		    window.location = $(this).attr('data-url');
		});
  };

  _deleteMapping = function(context) {
    var ok, form;
    ok = confirm('You are about to delete the ceremony mapping for ' + context + '.\nAre you sure you want to continue?');
    if (ok !== true) {
      return;
    }
    form = document.getElementById('ceremony-mapping-form');
    form.action = '/collation/projectsummary/ceremonymapping/delete';
    form.submit();
  };

  _isValidMapping = function(key, string) {
    var re;
    if (key === 'context') {
      re = /^Y.\d+.\d+.\d+$/;
      return re.test(string);
    } else {
      re = /^\w+.\d+.\d+.\d+(;\w+.\d+.\d+.\d+)*$/;
      return re.test(string);
    }
  };

  _validateCeremonyMapping = function(data) {
    var errors;
    errors = [];
    for (let key in data) {
      if (data.hasOwnProperty(key) && key !== 'csrfmiddlewaretoken') {
        if (data[key] !== '') {
          if (!_isValidMapping(key, data[key])) {
            errors.push(key);
          }
        }
      }
    }
    if (errors.length === 0) {
      return [true];
    } else {
      return [false, errors];
    }
  };

  _saveCeremonyList = function () {
    var form;
    form = document.getElementById('ec_form');
    form.action = '/collation/projectsummary/ceremonies/add';
    form.submit();
  };

  _saveCeremonyMapping = function() {
    var data, valid, form;
    data = forms.serialiseForm('cm_form');
    valid = _validateCeremonyMapping(data);
    if (valid[0] === false) {
      // show the errors
      for (let i=0; i<valid[1].length; i+=1) {
        $('#' + valid[1][i]).addClass('error');
      }
      return;
    }
    form = document.getElementById('cm_form');
    form.action = '/collation/projectsummary/ceremonymapping/add';
    form.submit();
  };

  _populateForm = function (context, details) {
    details = details.replace(/\'/g, '"');
    details = JSON.parse(details);
    document.getElementById('context').value = context;
    for (let key in details) {
      if (details.hasOwnProperty(key)) {
        document.getElementById('ceremony_' + key).value = details[key];
      }
    }
  };

  _addDeleteFunctions = function () {
    $('#delete_ceremonies_button').off('click');
    $('#delete_ceremonies_button').on('click', function (e) {
        let ok, ceremonies_selected = [];
        $("input[type='checkbox'][name='ceremony']:checked").each(
            function () {
                ceremonies_selected.push($(this).val());
            }
        );
        ok = confirm('Deleting the selected ceremonies from the list will also delete all of the data stored in ' +
                     'the existing mappings for these ceremonies.\nThis will happen when you press save.\n\n' +
                     'Please click ok to confirm that this is what you want.');
        if (ok) {
            for (let i=0; i<ceremonies_selected.length; i+=1) {
                document.getElementById('ceremonies').removeChild(document.getElementById(ceremonies_selected[i]));
            }
        } else {
            //uncheck everything and return
            $("input[type='checkbox'][name='ceremony']").each(
                function () {
                    $(this).prop('checked', false);
                }
            );
            return;
        }
    });
  };

  _addCeremony = function (identifier) {
    var list, li;
    list = document.getElementById('ceremonies');
    li = document.createElement('li');
    li.setAttribute('id', identifier);
    li.innerHTML = identifier + '<input type="hidden" name="' + identifier + '" value="' + identifier + '"/>' +
                   '<label for="checkbox_' + identifier + '" class="visuallyhidden">Select ' + identifier + ' for deleting</label>' +
                   '<input id="checkbox_' + identifier + '" type="checkbox" class="delete_ceremony" value="' + identifier + '" name="ceremony"/>';
    list.appendChild(li);
  };

  _displayCeremonyEditForm = function () {
    var form, left, url;
    if (document.getElementById('add_edit_cm_div')) {
      document.getElementsByTagName('body')[0].removeChild(document.getElementById('add_edit_cm_div'));
    }
    form = document.createElement('div');
    form.id = 'add_edit_cm_div';
    document.getElementsByTagName('body')[0].appendChild(form);
    form.style.top = '10px';
    form.style.left = '20px';
    url = staticUrl + 'collation/html_fragments/edit_ceremonies_list_form.html';

    $.ajax({
      'url': url,
      'method': 'GET'
    }).then(function(html) {
      var ceremonies, ceremoniesHTML;
      form.innerHTML = html;
      ceremonies = document.getElementById('ceremony_list').value.split('|');
      for (let i=0; i<ceremonies.length; i+=1) {
        _addCeremony(ceremonies[i]);
      }
      slist('ceremonies');
      document.getElementById('csrf_token').value = $("input[name='csrfmiddlewaretoken']").val();
      drag.initDraggable('add_edit_cm_div', true, true);
      $('#add_ceremony_button').off('click.acb');
      $('#add_ceremony_button').on('click.acb', function() {
        var newCeremony;
        newCeremony = document.getElementById('new_ceremony').value;
        if (newCeremony !== '') {
          _addCeremony(newCeremony);
          document.getElementById('new_ceremony').value = '';
        }
      });
      $('#save_ceremonies_button').off('click.amb');
      $('#save_ceremonies_button').on('click.amb', function() {
        _saveCeremonyList();
      });
      $('#cancel_button').off('click.cb');
      $('#cancel_button').on('click.cb', function() {
        document.getElementById('add_edit_cm_div').parentNode.removeChild(document.getElementById('add_edit_cm_div'));
      });
      _addDeleteFunctions();
    });
  };

  _displayAddEditForm = function(projectId, mode, callback) {
    var form, left, url;
    if (document.getElementById('add_edit_cm_div')) {
      document.getElementsByTagName('body')[0].removeChild(document.getElementById('add_edit_cm_div'));
    }
    form = document.createElement('div');
    form.id = 'add_edit_cm_div';
    document.getElementsByTagName('body')[0].appendChild(form);
    form.style.top = '10px';
    form.style.left = '20px';
    url = staticUrl + 'collation/html_fragments/add_edit_ceremony_mapping_form.html';

    $.ajax({
      'url': url,
      'method': 'GET'
    }).then(function(html) {
      var ceremonies, ceremoniesHTML;
      form.innerHTML = html;
      ceremonies = document.getElementById('ceremony_list').value.split('|');
      ceremoniesHTML = [];
      for (let i=0; i<ceremonies.length; i+=1) {
        ceremoniesHTML.push('<label for="ceremony_' + ceremonies[i] + '">' + ceremonies[i] + ':</label>');
        ceremoniesHTML.push('<input type="text" id="ceremony_' + ceremonies[i] + '" name="ceremony_' + ceremonies[i] + '"/><br/>');
      }
      document.getElementById('ceremonies').innerHTML = ceremoniesHTML.join('');
      document.getElementById('csrf_token').value = $("input[name='csrfmiddlewaretoken']").val();
      drag.initDraggable('add_edit_cm_div', true, true);

      if (callback) {
        callback();
      }

      $('#add_mappings_button').off('click.amb');
      $('#add_mappings_button').on('click.amb', function() {
        _saveCeremonyMapping();
      });

      $('#cancel_button').off('click.cb');
      $('#cancel_button').on('click.cb', function() {
        document.getElementById('add_edit_cm_div').parentNode.removeChild(document.getElementById('add_edit_cm_div'));
      });
    });
  };

  return {};

}());
