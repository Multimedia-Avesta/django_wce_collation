/*jshint esversion: 6 */
supplements = (function () {
    "use strict";

    var _addHandlers, _addDeleteFunctions;

    $(document).ready(function () {
      var i;
      _addHandlers();
      i = 0;
      while (document.getElementById('units_' + i)) {
        _addDeleteFunctions(i);
        i+=1;
      }
    });

    _addHandlers = function () {
      $('.add-button').on('click', function (e) {
        var buttonId, counter, values, li;
        buttonId = e.target.id;
        counter = buttonId.replace('add_siglum_', '');
        values = $('#units_' + counter).val();
        for (let i=0; i<values.length; i+=1) {
          if (values[i] != 'none') {
            li = document.createElement('li');
            li.innerHTML = values[i] + '<input type="hidden" value="' + values[i] + '" name="units_' + counter + '"/>' +
                           '<img alt="delete logo" class="delete_img delete_unit_' + counter + '" src="' + staticUrl + '/collation/images/delete.png"/>';
            document.getElementById('siglum_list_' + counter).appendChild(li);
            $('#units_' + counter + ' option[value="' + values[i] + '"]').prop('disabled', true);
          }
        }
        _addDeleteFunctions(counter);
        document.getElementById('units_' + counter).value = null;
      });
      $('#save-button').on('click', function () {
        $('#supplement-range-form').submit();
      });
      $('.delete-button').on('click', function (e) {
          let ok;
          ok = confirm('This will delete all of the supplements data stored for this transcription.\n' +
                       'The data will be immediately deleted from the screen but will not be deleted from ' +
                       'the database until you save the changes.\n\n' +
                       'Are you sure you want to continue?');
         if (ok) {
             e.target.parentElement.parentElement.removeChild(e.target.parentElement);
         } else {
             return;
         }
      });
      // $('#back-button').on('click', function () {
      //   window.location.href = '/collation/projectsummary';
      // });
    };

    _addDeleteFunctions = function (counter) {
      $('.delete_unit_' + counter).off('click');
      $('.delete_unit_' + counter).on('click', function (e) {
        var parent, value, index;
        parent = e.target.parentElement;
        value = $(parent).find('input')[0].value;
        $('#units_' + counter + ' option[value="' + value + '"]').prop('disabled', false);
        document.getElementById('siglum_list_' + counter).removeChild(parent);
      });
    };

    return {};

  } () );
