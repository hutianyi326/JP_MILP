$(function(){
  
  var now = new Date();
  var y = now.getFullYear();
  var m = now.getMonth() + 1;
  var file1 =  "eria_jukyu_";
  var ext1 =  "_07.csv";

  min_y=2024;
  
  updateMonth(y, min_y);

  $("#year1").val(y);
  $("#month1").val(m);

  var url = getUrl1($("#year1").val(),$("#month1").val(),file1,ext1);
  stateChange(url);

  $("#year1").change(function() {
    var url = getUrl1($("#year1").val(),$("#month1").val(),file1,ext1);
    stateChange(url);
  });
  $("#month1").change(function() {
    var url = getUrl1($("#year1").val(),$("#month1").val(),file1,ext1);
    stateChange(url);
  });
  $("#download1").click(function() {
    var url = getUrl1($("#year1").val(),$("#month1").val(),file1,ext1);
    doDownload(url);
  });
});


function stateChange(url) {
  download1Disabled();

  var xhr = new XMLHttpRequest();
  xhr.open("GET", url, true);
  xhr.onload = function (e) {
    if (xhr.readyState === 4) {
      if (xhr.status === 200) {
        download1Enabled();
      }
    }
  };
  xhr.send();
}

function getUrl1(y, m, file, ext) {
  var now = new Date();
  var url = "sys/"
          + file
          + ('0000' + $("#year1").val()).slice(-4)
          + ('00'+$("#month1").val()).slice(-2)
          + ext
          + '?ver=' + now.getTime();
  return url;
}

function download1Enabled() {
  $("#download1").prop('disabled', false);
}

function download1Disabled() {
  $("#download1").prop('disabled', true);
}

function doDownload(url) {
  var alink = document.createElement('a');
  alink.href = url;
  alink.click();
  return false;
}


function updateMonth(y, min_y) {
  var select = document.getElementById('year1');
  while (0 < select.childNodes.length) {
    select.removeChild(select.childNodes[0]);
  }

  for (var i = min_y; i <= y; i++) {
    var option = document.createElement('option');
    option.value = i;
    option.textContent = i+'年';
    select.appendChild(option);
  }
}