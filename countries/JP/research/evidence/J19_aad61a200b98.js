function getCSV(file,fileDir,fileType){
	let fileName = "/js/csv_read.php?dir=" + fileDir + "&file=" + file;
  var req = new XMLHttpRequest(); // HTTPでファイルを読み込むためのXMLHttpRrequestオブジェクトを生成
  req.open("get", fileName, true); // アクセスするファイルを指定
  req.setRequestHeader('Pragma', 'no-cache'); 
	req.setRequestHeader('Cache-Control', 'no-cache'); 
	req.setRequestHeader('If-Modified-Since', 'Thu, 01 Jun 1970 00:00:00 GMT'); 
  req.send(null); // HTTPリクエストの発行

  // レスポンスが返ってきたらconvertCSVtoArray()を呼ぶ
  req.onload = function(){
		csv2json(req.responseText,fileType); 
  }
}

function csv2json(csvArray,fileType){
  let jsonArray = new Object;
  let jsonData;
  let RowArray = csvArray.split('\n');
  RowArray.shift();//1行目を削除
  let items = RowArray[0].split(',');
  for(let i = 0; i < RowArray.length; i++)
	{
		let cellArray = RowArray[i].split(',');
		let line = [];	 
		if(cellArray[0] != undefined && cellArray[0] != "")
		{
			for(let j = 0; j < (items.length); j++){
	        line[j] = cellArray[j];
	    }
			jsonArray[line[0]] = (line);
		}
	}	
	setData(jsonArray,fileType);
}

function compareFunc(a, b) {
  return b - a;
}


function setData(jsonArray,fileType)
{
	if(fileType == "commission")
	{
		let dateArr = new Array();
		Object.keys(jsonArray).forEach(function (key) {
		  dateArr.push(key);
		});
		dateArr.sort(compareFunc);
		dateArr.forEach((element,index) => {
			let active= "";
			if(index==0) 
			{
				$("#commission .year-select .year").text(element);
				active = " active";
			}
			let html = "";
		  	  html = '<div id="commission-data' + element + '" class="commission-data' + active + '">';
					html += '<table class="commission-data__table tb_hide">';
					html += '<thead><tr><th>スポット取引売買手数料（税抜）</th><th>時間前取引売買手数料（税抜）</th></tr></thead>';	   	
					html += '<tbody><tr><td>' + jsonArray[element][1] + '</td><td>' + jsonArray[element][3] + '</td></tr></tbody>';	 
					html += '</table>';	 
					html += '<table class="commission-data__table tb_show">';	
					html += '<thead><tr><th>スポット取引<br>売買手数料<br>（税抜）</th><td>' + jsonArray[element][1] + '</td></tr></thead>';	
					html += '<tbody><tr><th>時間前取引<br>売買手数料<br>（税抜）</th><td>' + jsonArray[element][3] + '</td></tr></tbody>';	
					html += '</table>';	
					if(jsonArray[element][2] != null && jsonArray[element][2] != "") 
					{
						html += '<p class="commission-data__bottom"><span class="commission-data__bottom__label">先渡定型取引売買手数料</span>' + jsonArray[element][2] + '</p>';	
					}
				  html += '</div>';	  
		  $("#commission-content").append(html);	
		  let yearHtml = '<li><a href="javascript:void(0)" data-date="' + element + '" data-section="commission"><span class="year">' + element + '</span>年度</a></li>';
		  $("#commission .year-list").append(yearHtml);  
		});	
	}
	else if(fileType == "co2")
	{
		let dateArr = new Array();
		Object.keys(jsonArray).forEach(function (key) {
		  dateArr.push(key);
		});
		dateArr.sort(compareFunc);
		dateArr.forEach((element,index) => {
			let active= "";
			if(index==0) 
			{
				$("#co2 .year-select .year").text(element);
				active = " active"
			}
			let html = "";
					html = '<div id="co2-data' + element + '" class="co2-data' + active + '">';
					html += '<table class="co2-data__table pc_only">';
					html += '<thead><tr><th>' + jsonArray[element][0] + '年度受渡分</th></tr></thead>';			   	
					html += '<tbody><tr><td>' + jsonArray[element][1] + '</td></tr></tbody>';		
					html += '</table>';
					html += '<table class="co2-data__table sp_only">';		
					html += '<tbody><tr><th>' + jsonArray[element][0] + '年度<br>受渡分</th><td>' + jsonArray[element][1] + '</td></tr></tbody>';
					html += '</table>';
					html += '</div>';
			$("#co2-content").append(html);
			let yearHtml = '<li><a href="javascript:void(0)" data-date="' + element + '" data-section="co2"><span class="year">' + element + '</span>年度</a></li>';
		  $("#co2 .year-list").append(yearHtml);  
		});	
	}
	else if(fileType == "annualfee")
	{
		let dateArr = new Array();
		Object.keys(jsonArray).forEach(function (key) {
		  dateArr.push(key);
		});
		dateArr.sort(compareFunc);
		dateArr.forEach((element,index) => {
			let active= "";
			if(index==0) 
			{
				$("#annualfee .year-select .year").text(element);
				active = " active"
			}
			let html = "";
					html = '<div id="annualfee-data' + element + '" class="annualfee-data' + active + '">';
					html += '<table class="annualfee-data__table pc_only">';
					html += '<thead><tr><th>' + jsonArray[element][0] + '年度年会費（不課税）</th></tr></thead>';			   	
					html += '<tbody><tr><td>' + jsonArray[element][1] + '</td></tr></tbody>';		
					html += '</table>';
					html += '<table class="annualfee-data__table sp_only">';		
					html += '<tbody><tr><th>' + jsonArray[element][0] + '年度<br>年会費<br>（不課税）</th><td>' + jsonArray[element][1] + '</td></tr></tbody>';
					html += '</table>';
					html += '</div>';
			$("#annualfee-content").append(html);
			let yearHtml = '<li><a href="javascript:void(0)" data-date="' + element + '" data-section="annualfee"><span class="year">' + element + '</span>年度</a></li>';
		  $("#annualfee .year-list").append(yearHtml);  
		});	
	}
	//URL hash link, after content is filled in
	var scrollSpeed = 500;
	var headerHeight = $("#header").height() + 20;
	var urlHash = location.hash;    //URLハッシュを取得
	if(urlHash) {
		$('body,html').stop().scrollTop(0);
		setTimeout(function(){
			var target = $(urlHash);
			var position = target.offset().top - headerHeight;
			$('body,html').stop().animate({scrollTop:position}, scrollSpeed);
		}, 100);
	}
}

window.addEventListener('load', () => {
	let fileNameArr = new Object();
	fileNameArr["commission"] = "commission_list.csv";
	fileNameArr["co2"] = "co2_emission_factor.csv";
	fileNameArr["annualfee"] = "annualfee_list.csv";
	getCSV(fileNameArr["commission"],"csv_editable","commission");
	getCSV(fileNameArr["co2"],"csv_editable","co2");
	getCSV(fileNameArr["annualfee"],"csv_editable","annualfee");
});