const start = performance.now();
let getGraphDateStatus = false;
let yearRangeVal = setYearRangeVal(2016);
let graphTypeArr = [
 "intraday"
];
let csvDateArr = new Object;
csvDateArr["intraday"] = new Object;
let latestDateArr = [];
let latestDate;
let minDateVal = new Date(2016, 4 - 1, 1);
let dateArr = new Object;
dateArr = new Object;
let dateArrAll = new Object;
dateArrAll["intraday"] = [];
let spotDataArr = [];
let spotDataAll = [];

let setGraph = false;
const seriesList = new Object;
seriesList["intraday"] = new Object;

//時間前市場
let intradayAllData = new Object;
let intradayAllTableData = new Object;
let intradayAllDataYear = [];
let intradayDataArrCount = 0;
let intradayData = new Object;
let intradayGraphArr = new Object;
intradayGraphArr = new Object;

let textLangArr = new Object;
let textArr = new Object;
textLangArr = {
	first_quotation : { 
		jp : "始値",
		en : "Opening Price"
	},
	highest_price : { 
		jp : "高値",
		en : "Highest Price"
	},
	lowest_price : { 
		jp : "安値",
		en : "Lowest Price"
	},
	closing_price : { 
		jp : "終値",
		en : "Last Price"
	},
	average : { 
		jp : "平均",
		en : "Average Price"
	},
	jpy : { 
		jp : "円",
		en : "JPY"
	},
	ymd : { 
		jp : "%Y年%m月%d日",
		en : "%d-%b-%Y"
	},
	total_contracted : { 
		jp : "約定総量",
		en : "Volume"
	},
	number_of_contracts : { 
		jp : "約定件数",
		en : "Number of Contracts"
	},
	"年度" : { 
		jp : "年度",
		en : ""
	},
	tooltip_format : { 
		jp : "{point.x:%Y/%m/%d %H:%M}",
		en : "{point.x:%d/%m/%Y %H:%M}"
	},
	date_format : { 
		jp : "%Y/%m/%d %H:%M",
		en : "%d-%b-%Y %H:%M"
	},
	date_format2 : { 
		jp : "%Y/%m/%d",
		en : "%d-%b-%Y"
	},
	date_format3 : { 
		jp : "-%Y/%m/%d",
		en : "-%d-%b-%Y"
	},
	date_format4 : { 
		jp : "%Y/%m",
		en : "%b-%Y"
	},
	date_format5 : { 
		jp : "-%Y/%m",
		en : "-%b-%Y"
	},
	date_format6 : { 
		jp : "%m/%d",
		en : "%d-%b"
	},
	date_format7 : { 
		jp : "-%m/%d",
		en : "-%d-%b"
	},
}

function convertMonth(num){
	if(num==1){
		return "Jan";
	}
	else if(num==2){
		return "Feb";
	}
	else if(num==3){
		return "Mar";
	}
	else if(num==4){
		return "Apr";
	}
	else if(num==5){
		return "May";
	}
	else if(num==6){
		return "Jun";
	}
	else if(num==7){
		return "Jul";
	}
	else if(num==8){
		return "Aug";
	}
	else if(num==9){
		return "Sep";
	}
	else if(num==10){
		return "Oct";
	}
	else if(num==11){
		return "Nov";
	}
	else{
		return "Dec";
	}
}

function setYearRangeVal(minDate)
{
	let yearRange = "";
	let today =  new Date();
	let nextYear =  new Date();
}

if($("html").hasClass("en-site"))
{
	Object.keys(textLangArr).forEach(function (key) {
		textArr[key] = textLangArr[key].en;
	});		
}
else
{
	Object.keys(textLangArr).forEach(function (key) {
		textArr[key] = textLangArr[key].jp;
	});	
}
console.log(textArr);

// Highchart全体設定
Highcharts.setOptions({
  global: {  // グローバルオプション
    useUTC: false   // GMTではなくJSTを使う
  },
  lang: {  // 言語設定
    rangeSelectorZoom: '',
    resetZoom: '表示期間をリセット',
    resetZoomTitle: '表示期間をリセット',
    rangeSelectorFrom: '',
    rangeSelectorTo: '〜',
    printButtonTitle: 'チャートを印刷',
    exportButtonTitle: '画像としてダウンロード',
    downloadJPEG: 'JPEG画像でダウンロード',
    downloadPDF: 'PDF文書でダウンロード',
    downloadPNG: 'PNG画像でダウンロード',
    downloadSVG: 'SVG形式でダウンロード',
    months: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
    weekdays: ['日', '月', '火', '水', '木', '金', '土'],
    numericSymbols: null   // 1000を1kと表示しない
  }
});

// Create the chart
Highcharts.setOptions({
	lang: {
  	thousandsSep: ','
  }
});

let marginLeft = undefined;

if($("html").hasClass("windows-os"))
{
	marginLeft = 100;
}

function getGraphDate(dir,action,dlFile,delivery_date_time,selectYear,selectDate)
{
	let fileName = "/js/get_graph_year.php?dir=" + dir;
	var req = new XMLHttpRequest();
	req.open("get", fileName, true);
	req.setRequestHeader('Pragma', 'no-cache'); 
	req.setRequestHeader('Cache-Control', 'no-cache'); 
	req.setRequestHeader('If-Modified-Since', 'Thu, 01 Jun 1970 00:00:00 GMT'); 
	req.send(null);
	
	req.onload = function(){
		if(req.responseText){
			var getyear = req.responseText.split(",");
			csvDateArr[dir]["latestYear"] = getyear[0];
			csvDateArr[dir]["oldYear"] = getyear[1];
			csvDateArr[dir]["countMax"] = csvDateArr[dir]["latestYear"] - csvDateArr[dir]["oldYear"] + 1;
			if(dir == "intraday")
			{
				if(action == "download")
				{
					SetDownload(dlFile);
				}
				else if(action == "init")
				{
					getGraphDateStatus = true;
					let xAxisMax = delivery_date_time;
					let jsonArray = new Array();
					if(selectYear < csvDateArr["intraday"]["oldYear"])
					{
						selectYear = csvDateArr["intraday"]["oldYear"];
					}
					if(selectYear <= csvDateArr["intraday"]["latestYear"])
					{
						//let xAxisMin = 
						dateArr[selectYear] = new Array();
						getCSV("intraday",selectYear,"intraday","create",selectDate,undefined,undefined,undefined,xAxisMax);						
					}
					else
					{
						filterLock();
						return false;
					}
				}
			}		
		}
	}
}

//csvの日付設定
//getGraphDate("intraday");

function getCSV(file,fileDate,fileType,dataStatus,selectDate,period,intradayData5yArrCount,selectYear,xAxisMax){
	let fileName = "/js/csv_read.php?dir=" + file + "&file=" + file + "_" + fileDate + ".csv";
	var req = new XMLHttpRequest(); // HTTPでファイルを読み込むためのXMLHttpRrequestオブジェクトを生成
	req.open("get", fileName, true); // アクセスするファイルを指定
	req.setRequestHeader('Pragma', 'no-cache'); 
	req.setRequestHeader('Cache-Control', 'no-cache'); 
	req.setRequestHeader('If-Modified-Since', 'Thu, 01 Jun 1970 00:00:00 GMT'); 
	req.send(null); // HTTPリクエストの発行
	
	// レスポンスが返ってきたらconvertCSVtoArray()を呼ぶ
	req.onload = function(){
	  if(fileType == "intraday")
	  {
		  //intradayAllData = intradayAllData.concat(csv2json(req.responseText,fileType,"all",fileDate,file));
		  if(period == "5year")
		  {
				csv2json(req.responseText,fileType,period,fileDate,file,dataStatus,selectDate);			
				if(intradayDataArrCount == intradayData5yArrCount)
				{
					let tradingYear = selectYear - 4;
					let jsonArray = new Array();
					if(tradingYear < csvDateArr["intraday"]["oldYear"])
					{
						tradingYear = csvDateArr["intraday"]["oldYear"];
					}
					console.log(Math.min.apply(null, dateArr[tradingYear]));
					let xAxisMin = Math.min.apply(null, dateArr[tradingYear]);
					for (let year = tradingYear; year <= selectYear; year++) {
						console.log(intradayAllData[year]);
						jsonArray = jsonArray.concat(intradayAllData[year]);
					}
					console.log("jsonArray",jsonArray);
					setGrafhPrice(jsonArray,selectYear,xAxisMax,xAxisMin,"create",undefined,period);
				}	  
		  }
		  else
		  {
			  csv2json(req.responseText,fileType,period,fileDate,file,dataStatus,selectDate,xAxisMax); 
		  }
	  }
  }
}

function SetDownload(dlFile)
{
	//DLデータセット
	let selectHtmlArr = new Object;
	selectHtmlArr["intraday"] = "";
	for (let year = csvDateArr["intraday"]["latestYear"]; year >= csvDateArr["intraday"]["oldYear"]; year--) {
		selectHtmlArr["intraday"] += '<option value="intraday_' + year + '.csv">'  + year + textArr["年度"] + '</option>';
	}
	$("#dl-select--intraday").html(selectHtmlArr["intraday"]);
	$("#data-area__filter .dl-button").removeClass("hide init");
	if(dlFile != undefined)
	{
		$(".overlay,#modal-box--" + dlFile).fadeIn("fast");
	}
}

function filterLock()
{
	$(".filter-section__button-list .button").not(".active").addClass("disabled").prop("disabled",true);	
	$(".filter-section--lock").addClass("disabled");
	$("#priceGraph").html("");
	$("#amountGraph").html("");
	$("#numberGraph").html("");
	$("#intraday__table tbody").html("");	
	$(".graph-section__content-wrapper,.table-section__table-area-wrap").addClass("hide");
}

function graphFilterSet()
{
	let type = $("#filter-section--type .button.active").data("type");
	$(".filter-section__button-list .button").removeClass("disabled").prop("disabled",false);	
	if(type == "graph")
	{
		$(".filter-section").removeClass("disabled");	
	}
	else
	{
		$("#filter-section--detail").removeClass("disabled");	
	}
	$(".graph-section__content-wrapper,.table-section__table-area-wrap").removeClass("hide");
}

function csv2json(csvArray,fileType,period,fileDate,file,dataStatus,selectDate,xAxisMax){
	let jsonArray = [];
	let jsonData;
	let RowArray = csvArray.split('\n');
	RowArray.shift();//1行目を削除
	let items = RowArray[0].split(',');
	console.log(RowArray.length);
	if(fileType == "intraday")
	{
	  for(let i = 0; i < RowArray.length; i++){
	    let cellArray = RowArray[i].split(',');
	    let line = [];
	    if(cellArray[0] != undefined && cellArray[0] != "")
	    {
		    let csvDate = cellArray[0];
		    if(intradayAllTableData[csvDate] == undefined)
		    {
		      intradayAllTableData[csvDate] = new Object;
		    }			 
				intradayAllTableData[csvDate][cellArray[1]] = new Array();
		    
		    let date = new Date(cellArray[0]);
		    //console.log(date);
		    //console.log(cellArray);
		    let csv_date_unixtime = date.getTime() + ((Number(cellArray[1]) - 1)*1800*1000);
		    //console.log(new Date(csv_date_unixtime));
		    line[0] = csv_date_unixtime;
				dateArrAll[fileType].push(line[0]);
				dateArr[fileDate].push(line[0]);
				if(fileDate == csvDateArr[fileType]["latestYear"]) //最新のデータの日付
				{
					latestDateArr.push(line[0]);
				}
		    for(let j = 2; j < (items.length); j++){
		      	line[j] = cellArray[j];
		    }
				jsonArray.push(line);
				intradayAllTableData[csvDate][cellArray[1]].push(line);
			}
		}
		intradayAllData[fileDate] = jsonArray;
		if(fileDate == csvDateArr[fileType]["latestYear"])
		{
			latestDate = Number(moment(Math.max.apply(null, latestDateArr)/1000,'X').format('YYYYMMDD'));
			let selectDateNumBefore = new Date(selectDate).toISOString();
			let selectDateNum = Number(moment(selectDateNumBefore).format('YYYYMMDD'));
			if(latestDate >= selectDateNum)
			{
				if(period == "5year")
				{
					intradayDataArrCount = intradayDataArrCount + 1;
					return jsonArray;
				}
				else
				{
					setGrafhPrice(jsonArray,fileDate,xAxisMax,undefined,dataStatus,selectDate);	
				}		
			}
			else
			{
				filterLock();
				return false;
			}		
		}
		else
		{
			if(period == "5year")
			{
				intradayDataArrCount = intradayDataArrCount + 1;
				return jsonArray;
			}
			else
			{
				setGrafhPrice(jsonArray,fileDate,xAxisMax,undefined,dataStatus,selectDate);	
			}
		}
	}
}

function utc2dateString(utc_msec) {
  d=new Date();
  d.setTime(utc_msec);
  return d.getFullYear()+'/'+(d.getMonth()+1)+'/'+d.getDate();
}

function graphSetCheck(file)
{
	setGraph = true;
	for (let year = csvDateArr[file]["oldYear"]; year <= csvDateArr[file]["latestYear"]; year++) {
	 	if(!$("#graph-section--real-num_" + year).find(".highcharts-container").length)
	 	{
	 		setGraph = false; 		
	 	}
	 	if(!$("#graph-section--real-num_" + year).find(".highcharts-container").length)
	 	{
			setGraph = false; 	
	 	}
	}
}

function compareFunc(a, b) {
  return b - a;
}

function setTableCell(cellData)
{
	if(Number(cellData))
	{
		cellData = Number(cellData).toLocaleString();
	}
	return cellData;
}

function setNumberCheck(number)
{
	if(Number(number))
	{
		number = Number(number);	
	}
	else
	{
		number = null;
	}
	return number;
}

function setTooltipData(tooltipData)
{
	if(Number(tooltipData))
	{
		tooltipData = Number(tooltipData).toFixed(2);	
	}
	return tooltipData;
}

function setGrafhCalendar()
{	
	/*-----------------------------------------
	Calender
	-------------------------------------------*/
	$("#datepicker").datepicker({
		changeMonth: true,
		changeYear: true,
		minDate: minDateVal,
		yearRange: '2016:+1',
	  onSelect: function(dateText, inst){
		 let selectYear;
		 $("#datepicker-area").fadeOut();	
		 console.log(dateText);
		let selectDate;
		 if($("html").hasClass("en-site"))
		 {
			 let selectDateBefore = new Date(dateText).toISOString();
			 selectDate = moment(selectDateBefore).format('YYYY/MM/DD');
		 }
		 else
		 {
			 selectDate = dateText;
		 }
		 let ymdArr = selectDate.split('/');
		 $("#datepicker--date__year").text(ymdArr[0]);
		 if($("html").hasClass("en-site")){
				$("#datepicker--date__month").text(convertMonth(ymdArr[1]));
			}
			else{
				$("#datepicker--date__month").text(ymdArr[1]);
			}
		 $("#datepicker--date__day").text(ymdArr[2]);
		 $("#button--calender-show").hide();
		 $("#datepicker--date").removeClass("hide");
		 
			
			 let dates = dateText.split('/');
			 let trading_date  = new Date(dateText);
			 let delivery_date = new Date(trading_date.getFullYear(), trading_date.getMonth(), trading_date.getDate() ,23,30);
			 let trading_date_all;
			 let dataMinDate = Math.min.apply(null, dateArr[trading_date.getFullYear()]);
			 let yyyy = trading_date.getFullYear();			 
			 if((trading_date.getMonth() + 1) < 4)//1〜3月の場合
			 {
				 dataMinDate = Math.min.apply(null, dateArr[trading_date.getFullYear() - 1]);
				 yyyy = trading_date.getFullYear() - 1; 
				 selectYear = Number(ymdArr[0] - 1);
			 }		
			 else
			 {
			 	selectYear = ymdArr[0];
			 }	 
			 switch ($("#filter-section--period input:checked").val()) {
			  case "day":
			    selectedPeriod = 1;
			    trading_date_all = trading_date;
			    break
			  case "month":
			    selectedPeriod = 2;
			    if(compareMonthDay(selectDate))
			    {
				    trading_date_all = new Date(trading_date.getFullYear(), trading_date.getMonth(), 1);
			    }
			    else
			    {
				    trading_date_all = new Date(trading_date.getFullYear(), trading_date.getMonth() - 1, trading_date.getDate(), trading_date.getHours());
			    }
			    break
			  case "year":
			    selectedPeriod = 3;
			    trading_date_all = new Date(trading_date.getFullYear() - 1, trading_date.getMonth(), trading_date.getDate(), trading_date.getHours());
			    break
			  case "5year":
			    selectedPeriod = 4;
			    trading_date_all = new Date(trading_date.getFullYear() - 5, trading_date.getMonth(), trading_date.getDate(), trading_date.getHours());
			    break
			  default:
					selectedPeriod = 1;    
					trading_date_all = trading_date;
			}
			
			let delivery_date_time = delivery_date.getTime();
			let trading_date_time = trading_date_all.getTime();		 
			if(trading_date_time < dataMinDate)
			{
			 trading_date_time = dataMinDate;
			}	
			if(intradayAllData[selectYear] == undefined)
			{
				$("#priceGraph").html("");
				$("#amountGraph").html("");
				$("#numberGraph").html("");
				$("#intraday__table tbody").html("");
				
				if(!getGraphDateStatus)
			  {
				  getGraphDate("intraday","init",undefined,delivery_date_time,selectYear,selectDate);
			  }
			  else
			  {
				  if(selectYear > csvDateArr["intraday"]["latestYear"])
					{
						filterLock();
					}
					else
					{
						let xAxisMax = delivery_date_time;
						if(selectYear < csvDateArr["intraday"]["oldYear"])
						{
							selectYear = csvDateArr["intraday"]["oldYear"];
						}
						dateArr[selectYear] = new Array();
						if($("#filter-section--period input:checked").val() == "5year")
						{
							intradayDataArrCount = 0;
							let intradayData5yArrCount = 0;
							let tradingYear = yyyy - 4;
							let jsonArray = new Array();
							if(tradingYear < csvDateArr["intraday"]["oldYear"])
							{
								tradingYear = csvDateArr["intraday"]["oldYear"];
							}
							console.log(Math.min.apply(null, dateArr[tradingYear]));
							let status = "update";
							let xAxisMax = delivery_date_time;
							for (let year = tradingYear; year <= selectYear; year++) {
								if(!intradayAllData[year])
								{
									dateArr[year] = new Array();
									intradayData5yArrCount = intradayData5yArrCount + 1;	
									status = "create";
								}
							}
							if(status == "create")
							{
								for (let year = tradingYear; year <= selectYear; year++) {
									if(!intradayAllData[year])
									{
										getCSV("intraday",year,"intraday",undefined,undefined,"5year",intradayData5yArrCount,selectYear,xAxisMax);		
									}
								}
							}
						}
						else
						{
							getCSV("intraday",selectYear,"intraday","create",selectDate,undefined,undefined,selectYear,xAxisMax);
						}				
					}
					//getCSV("intraday",year,"intraday",undefined,undefined,"5year",intradayData5yArrCount,selectYear,xAxisMax);	
				}
			}
			else
			{
			let selectDateNumBefore = new Date(selectDate).toISOString();
			let selectDateNum = Number(moment(selectDateNumBefore).format('YYYYMMDD'));
			if(selectYear == csvDateArr["intraday"]["latestYear"] && latestDate < selectDateNum)
			{
				filterLock();
			}
			else
			{
				graphFilterSet();
				//表の値変更
			  let html =  "";
			  for (let i = 1; i <=  Object.keys(intradayAllTableData[selectDate]).length; i++){
				  console.log(intradayAllTableData[selectDate][i][0][0]);
					let spotTime = moment(intradayAllTableData[selectDate][i][0][0]/1000,'X').format('HH:mm');
					let csv_next_unixtime = intradayAllTableData[selectDate][i][0][0] + (1800*1000);
					let spotNextTime = moment(csv_next_unixtime/1000,'X').format('HH:mm');
				  //約定価格
				  html += "<tr>";
					html += "<td>" + spotTime + "-" + spotNextTime + "</td>";
					for (let j = 2; j <= 8; j++){
						if(j == 7)
						{
							html += "<td class='cell--number'>" + setTableCell(intradayAllTableData[selectDate][i][0][j]) + "</td>";
						}
						else
						{
							html += "<td class='cell--number'>" + intradayAllTableData[selectDate][i][0][j] + "</td>";
						}
					}
					html += "</tr>";
				}
				$("#intraday__table .graph-section__table tbody").html(html);
				
				if($("#filter-section--period input:checked").val() == "5year")
				{
					let tradingYear = yyyy - 4;
					let selectYear = yyyy;
					let checkFlag;
					if(tradingYear < csvDateArr["intraday"]["oldYear"])
					{
						tradingYear = csvDateArr["intraday"]["oldYear"];
					}
					checkFlag = checkSet5year(tradingYear,yyyy);
					if(checkSet5year(tradingYear,yyyy))
					{
						trading_date_time = Math.min.apply(null, dateArr[tradingYear]);
						if((trading_date.getMonth() + 1) < 4)//1〜3月の場合
						{
						 trading_date_time = Math.min.apply(null, dateArr[tradingYear - 1]);
						}	
						if($("#priceGraph_" + yyyy).length)
						{
						 intradayGraphArr["price"].xAxis[0].setExtremes(trading_date_time,delivery_date_time);
						 intradayGraphArr["price"].redraw();
						 intradayGraphArr["amount"].xAxis[0].setExtremes(trading_date_time,delivery_date_time);
						 intradayGraphArr["amount"].redraw();
						 intradayGraphArr["number"].xAxis[0].setExtremes(trading_date_time,delivery_date_time);
						 intradayGraphArr["number"].redraw();
					 }
					 else
					 {
						let jsonArray = new Array();
						let xAxisMin = Math.min.apply(null, dateArr[tradingYear]);
						let xAxisMax = delivery_date_time;
						for (let year = tradingYear; year <= selectYear; year++) {
							console.log(intradayAllData[year]);
							jsonArray = jsonArray.concat(intradayAllData[year]);
						}
						console.log("jsonArray",jsonArray);
						$(".intradayGraph").removeClass("period1YGraph");
						setGrafhPrice(jsonArray,selectYear,xAxisMax,xAxisMin);		 
					 }
					}	
					else
					{
						let period = "5year";
						let xAxisMax = delivery_date_time;
						let selectYear = yyyy;
						set5year(selectYear,xAxisMax,period);
					}
				}
				else
				{
					if($("#priceGraph_" + yyyy).length)
				 {
					 intradayGraphArr["price"].xAxis[0].setExtremes(trading_date_time,delivery_date_time);
					 intradayGraphArr["price"].redraw();
					 intradayGraphArr["amount"].xAxis[0].setExtremes(trading_date_time,delivery_date_time);
					 intradayGraphArr["amount"].redraw();
					 intradayGraphArr["number"].xAxis[0].setExtremes(trading_date_time,delivery_date_time);
					 intradayGraphArr["number"].redraw();
				 }
				 else
				 {
					let xAxisMax = delivery_date_time;
					let selectYear = yyyy;
					let jsonArray = intradayAllData[yyyy];
					setGrafhPrice(jsonArray,yyyy,xAxisMax,undefined,undefined,selectDate);
				 }
				}
			 }
			}
		}
  });	
	$("#datepicker--date-wrap").fadeIn();
	$("#datepicker--date").on("click",function(){
		$("#datepicker-area").fadeToggle();
	});
}

function getAverageData(arrayData)
{
	let total = arrayData.reduce(function(sum, element){
		if(element)
		{
			return sum + element;		
		}
	}, 0);		
	let average = total/arrayData.length;
	return Math.round(average);
}

//選択月と前月の日付を比較
function compareMonthDay(selectDate)
{
	let date = new Date(selectDate);
	let lastMonthDay = getLastMonthDay(selectDate);
	if(date.getDate() > lastMonthDay.getDate())
	{
		return true;
	}
	else
	{
		return false;
	}
}

//選択した日付の月の日数
function getLastDay(selectDate)
{
	let date = new Date(selectDate);
	let year = date.getFullYear();
	let month = date.getMonth() + 1;
	let lastDay = new Date(year,month,0);
	return lastDay;
}

//選択した日付の前月の日数
function getLastMonthDay(selectDate)
{
	let date = new Date(selectDate);
	let year = date.getFullYear();
	let month = date.getMonth();
	let lastMonthDay = new Date(year,month,0);
	return lastMonthDay;
}


//月の日数を時間に変換
function setMonthTime(selectDate)
{
	let date = new Date(selectDate);
	let lastDay = getLastDay(selectDate);
	let lastMonthDay = getLastMonthDay(selectDate);	
	let dateCount;
	let dayDiff;
	if(lastDay.getDate() == lastMonthDay.getDate())
	{
		dateCount = ((lastDay.getDate()+1)*24) - 0.5;
	}
	else if(lastDay.getDate() > lastMonthDay.getDate())
	{
		if(date.getDate() > lastMonthDay.getDate())
		{
			dayDiff = date.getDate() - lastMonthDay.getDate();
			dateCount = (lastMonthDay.getDate() + dayDiff)*24 - 0.5;	
		}
		else
		{
			dayDiff = lastMonthDay.getDate() - lastDay.getDate() + 1;
			dateCount = (lastDay.getDate() + dayDiff)*24 - 0.5;	
		}
	}
	else
	{
		dayDiff = lastMonthDay.getDate() - lastDay.getDate() + 1;
		dateCount = (lastDay.getDate() + dayDiff)*24 - 0.5;	
	}
	return dateCount;
}

function setGrafhPrice(jsonArray,fileDate,xAxisMax,xAxisMin,dataStatus,selectDate,period)
{
	if(period == "5year" && $("#filter-section--period input:checked").val() != period)
	{
		return false;
	}
	graphFilterSet();
	
	let xAxisMaxVal = undefined;
	let xAxisMinVal = undefined;
	let htmlGraphArr = new Object;
	let selectDateVal = selectDate;
	htmlGraphArr["price"] = '<div id="priceGraph_' + fileDate + '" class="period1YGraph priceGraph intradayGraph spotGraph_' + fileDate + '">';
	htmlGraphArr["amount"] = '<div id="amountGraph_' + fileDate + '" class="period1YGraph amountGraph intradayGraph spotGraph_' + fileDate + '">';
	htmlGraphArr["number"] = '<div id="numberGraph_' + fileDate + '" class="period1YGraph numberGraph intradayGraph spotGraph_' + fileDate + '">';
	$("#priceGraph").html(htmlGraphArr["price"]);
	$("#amountGraph").html(htmlGraphArr["amount"]);
	$("#numberGraph").html(htmlGraphArr["number"]);
	
	
	switch ($("#filter-section--period input:checked").val()) {
	  case "day":
	    graphSelectedPeriod = 0;
	    break
	  case "month":
	    graphSelectedPeriod = 1;
	    break
	  case "year":
	    graphSelectedPeriod = 2;
	    break
	  case "5year":
	    graphSelectedPeriod = 3;
	    break
	  default:
			graphSelectedPeriod = 0;    
	}
	
	if(xAxisMax)
	{
		xAxisMaxVal = xAxisMax;
	}
	
	if(xAxisMin)
	{
		xAxisMinVal = xAxisMin;
	}
		
	//約定価格
	priceData = jsonArray.map(x => [x[0], setNumberCheck(x[2]), setNumberCheck(x[3]), setNumberCheck(x[4]), setNumberCheck(x[5]), Number(x[6])]);
	let seriesDataArr = new Object;
	seriesDataArr["price"] = [
		{
      data: priceData,
      id: 'data',
      color: "#24B9FD",
      upColor: '#D0177A',
      name: '',
        type: 'candlestick'
    },
/*
    {
		  type: 'sma',
		  linkedTo: 'data',
		  zIndex: 1,
		  marker: {
		      enabled: false
		  }
		}
*/
	];
	intradayGraphArr["price"] = Highcharts.stockChart('priceGraph_' + fileDate, {
		chart: {
			 height: 500,
			 marginLeft: marginLeft
		},
		credits: {
      enabled: false
    },
	  plotOptions: {
	    candlestick: {
	      color: '#277AB4',
	      tooltip: {
	        dateTimeLabelFormats: {
	          millisecond: ['%Y/%m/%d %H:%M:%S.%L', '%Y/%m/%d %H:%M:%S.%L', '-%H:%M:%S.%L'],
	           second: ['%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '-%H:%M:%S'],
	           minute: [textArr["date_format"], textArr["date_format"], '-%H:%M'],
	           hour: [textArr["date_format"], textArr["date_format"], '-%H:%M'],
	           day: [textArr["date_format2"], textArr["date_format2"], textArr["date_format3"]],
	           week: [textArr["date_format2"], textArr["date_format2"], textArr["date_format3"]],
	           month: [textArr["date_format4"], textArr["date_format4"], textArr["date_format5"]],
	           year: ['%Y', '%Y', '-%Y']
	        }
	      }
	    },
	    series: {
	      // general options for all series
	    },
	    sma: {
	      enableMouseTracking: false,
	      lineWidth: 1,
	      marker: {
	        radius: 0
	      }
	    }
	  },
	  tooltip: {
	   formatter: function () {
		   		let thisDate = Highcharts.dateFormat(textArr["date_format"], this.x);
		   		console.log('dataGroup', this);
		   		console.log('data', priceData);
		   		let index = priceData.findIndex(([x]) => x === this.x);
		   		console.log("index",index);
		   		console.log("平均",priceData[index][5]);
		   		let html = "";
		   		if($("html").hasClass("en-site") && window.matchMedia('screen and (max-width:1023px)').matches)
		   		{
			   		html += textArr["first_quotation"] + "<br>" + priceData[index][1].toFixed(2) + "(" + textArr["jpy"] + "/kWh)" + "<br>";
			   		html += textArr["highest_price"] + "<br>" + priceData[index][2].toFixed(2) + "("  + textArr["jpy"] + "/kWh)" + "<br>";
			   		html += textArr["lowest_price"] + "<br>" + priceData[index][3].toFixed(2) + "("  + textArr["jpy"] + "/kWh)" +  "<br>";
			   		html += textArr["closing_price"] + "<br>" + priceData[index][4].toFixed(2) + "(" + textArr["jpy"] + "/kWh)" +  "<br>";
			   		html += textArr["average"] + "<br>" + priceData[index][5].toFixed(2) + "(" + textArr["jpy"] + "/kWh)" +  "<br>";
		   		}
		   		else
		   		{
			   		html += textArr["first_quotation"] + "：" + priceData[index][1].toFixed(2) + "(" + textArr["jpy"] + "/kWh)" + "<br>";
			   		html += textArr["highest_price"] + "：" + priceData[index][2].toFixed(2) + "("  + textArr["jpy"] + "/kWh)" + "<br>";
			   		html += textArr["lowest_price"] + "：" + priceData[index][3].toFixed(2) + "("  + textArr["jpy"] + "/kWh)" +  "<br>";
			   		html += textArr["closing_price"] + "：" + priceData[index][4].toFixed(2) + "(" + textArr["jpy"] + "/kWh)" +  "<br>";
			   		html += textArr["average"] + "：" + priceData[index][5].toFixed(2) + "(" + textArr["jpy"] + "/kWh)" +  "<br>";
		   		}
		   		console.log(priceData);
          return [thisDate, html]
      }
		},
	  navigator: {
	     xAxis: {
		     max: undefined,
		     min: xAxisMinVal,
            dateTimeLabelFormats: {
		          day:  textArr["date_format4"],
		          week: textArr["date_format4"],
		          month:textArr["date_format4"],
		          year: textArr["date_format4"]
		        },
            labels: {
				      style: {
				          color: 'black',
				          fontFamily: 'Oswald',
				      }
			      },
        }
	  },
	  yAxis: {
	    labels: {
	      style: {
	          color: 'black',
	          fontFamily: 'Oswald',
	      }
      },
	    title: {
	     text:  '(' + textArr["jpy"] + '/kWh)',
	     align: 'high',
	     offset: 0,
	     rotation: 0,
	     x:25,
       y: -10,
       style: {
           color: 'black'
       }
		  },
			opposite: false
	  },
	   xAxis: {
		  max: xAxisMaxVal,
		  min: xAxisMinVal,
			ordinal: false,
		  labels: {
	      style: {
	          color: 'black',
	          fontFamily: 'Oswald',
	      },
				formatter: function() {
        return Highcharts.dateFormat(this.dateTimeLabelFormat, this.value);
      	},	      
	    },
		  dateTimeLabelFormats: {
				 hour: ['%H:%M', '%H:%M', '-%H:%M'],
				 day: [textArr["date_format6"], textArr["date_format6"], textArr["date_format7"]],
				 week: [textArr["date_format6"], textArr["date_format6"], textArr["date_format7"]],
				 month: [textArr["date_format2"], textArr["date_format2"], textArr["date_format3"]],
         year: ['%Y', '%Y', '-%Y']
		  },
		  tickPositioner: function (min, max) {
          var xDataRange = max - min,
              positions = [],
              tick = min;

          positions.info = {higherRanks: {}};

          if (xDataRange <= 86400000) {
              // If range is 1 day max => 1 tick every hour
              increment = 3600000;
              positions.info.unitName = "hour";
          } else if (xDataRange > 86400000 && xDataRange <= 2678400000 + (86400000)) {
              // If range is between 1 day and 1 month => 1 tick every day
              increment = 86400000;
              positions.info.unitName = "day";
         } else if (xDataRange > 2678400000 + (86400000) && xDataRange <= 31536000000) {
              // If range is between 1 month and 1 year => 1 tick every month
              increment = 2678400000;
              positions.info.unitName = "month";
          } else {
              // If more than 1 year displayed, 1 tick every year
              increment = 365 * 24 * 60 * 60 * 1000;
              positions.info.unitName = "year";
              //$("#spotGraph1 .period1YGraph .highcharts-markers").hide();
          }
					
					let period = $("#filter-section--period input:checked").val();
          // Create ticks
          for(tick = min; tick - increment < max; tick += increment) {
            if(window.matchMedia('screen and (max-width:1600px)').matches)
            {
              if(tick == min)
              {
	            	positions.push(tick);  
              }
              if(period == "year" && tick >= max - increment)
              {
	            	positions.push(max);  
              }
              else if(period == "month" && tick >= max - increment)
              {
	            	positions.push(max);  
              }
              else if(period == "5year" && tick >= max - increment)
              {
	              let maxDate = new Date(max);
	              let maxDateMonth = Number(maxDate.getMonth() + 1);
	              let maxYear = Number(maxDate.getFullYear());
	              if(maxDateMonth < 4)
	              {
		            	maxYear = maxYear - 1; 
	              }
	              maxDate = new Date(maxYear,3,1, 23,30);
	              console.log("maxDate",maxDate);
	            	positions.push(maxDate.getTime());  
              }
							else if(tick < max && tick >= max - increment)
              {
	            	positions.push(tick);  
              }
            }
            else
            {
              positions.push(tick);
            }
          }
          positions.info.totalRange = positions[positions.length - 1] - positions[0];
          return positions;
      }
	  },
	 rangeSelector: {
	    inputDateFormat: textArr["ymd"],
			inputEditDateFormat: textArr["ymd"],
      allButtonsEnabled: true,
      buttons: [
      {
		    type: 'hour',
		    count: 23.5,
		    text: '1d',
		    title: 'View 1 day'
			}, 
      {
		    type: 'hour',
		    count: setMonthTime(selectDate),
		    text: '1m',
		    title: 'View 1 month'
		},{
		    type: 'year',
		    count: 1,
		    text: '1y',
		    title: 'View 1 year'
		}, {
		    type: 'year',
		    count: 5,
		    text: '5y',
		    title: 'View 5 year'
		}, 
		{
		    type: 'all',
		    text: 'All',
		    title: 'View all'
		}],
			labelStyle: {
	        color: '#277AB4',
	        fontFamily: 'メイリオ,sans-serif',
	    },
      selected: graphSelectedPeriod
    },
	  series: seriesDataArr["price"],
	  time: {
	    timezoneOffset: (new Date).getTimezoneOffset()
	  },
	  title: {
	    text: '値動き（'  + textArr["jpy"] + '/kWh）'
	  },
	  responsive: {
        rules: [
      	{
        	condition: {
              maxWidth: 767
          },
				  chartOptions: {
					  rangeSelector: {
					    inputPosition: {
					        align: 'left',
					        x: 0,
					        y: -20
					    },
					    buttonPosition: {
					        align: 'right',
					        x: 0,
					        y: 0
					    },
						},
					}
      	},
      ]
    }
	});
	
	//約定量
	let amountData = jsonArray.map(x => [x[0],Number(x[7])]);
	console.log(amountData);
	intradayGraphArr["amount"] = Highcharts.stockChart('amountGraph_' + fileDate, {
     navigator: {
        adaptToUpdatedData: false,
    },
    credits: {
      enabled: false
    },
    chart: {
        type: 'column',
    },
    plotOptions: {
      column: {
          pointPadding: 0.2,
          borderWidth: 0
      },
      tooltip: {
      dateTimeLabelFormats: {
        millisecond: ['%Y/%m/%d %H:%M:%S.%L', '%Y/%m/%d %H:%M:%S.%L', '-%H:%M:%S.%L'],
         second: ['%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '-%H:%M:%S'],
         minute: [textArr["date_format"], textArr["date_format"], '-%H:%M'],
         hour: [textArr["date_format"], textArr["date_format"], '-%H:%M'],
         day: [textArr["date_format2"], textArr["date_format2"], textArr["date_format3"]],
         week: [textArr["date_format2"], textArr["date_format2"], textArr["date_format3"]],
         month: ['%B %Y', '%B', '-%B %Y'],
         year: ['%Y', '%Y', '-%Y']
      }
     }
		},
    yAxis: { 
	    title: {
		     text: '(kWh)',
		     align: 'high',
		     offset: 0,
		     rotation: 0,
         y: -10 
		  },
		  opposite: false
	  },
	  navigator: {
	     xAxis: {
		     max: undefined,
				 min: xAxisMinVal,
            dateTimeLabelFormats: {
		          day:  textArr["date_format4"],
		          week: textArr["date_format4"],
		          month:textArr["date_format4"],
		          year: textArr["date_format4"]
		        },
            labels: {
				      style: {
				          color: 'black',
				          fontFamily: 'Oswald',
				      }
			      },
        }
	  },
	  xAxis: {
		  max: xAxisMaxVal,
			min: xAxisMinVal,
			ordinal: false,
		  labels: {
	      style: {
	          color: 'black',
	          fontFamily: 'Oswald',
	      },
	      formatter: function() {
        return Highcharts.dateFormat(this.dateTimeLabelFormat, this.value);
      	},		      
      },
		  dateTimeLabelFormats: {
         hour: ['%H:%M', '%H:%M', '-%H:%M'],
				 day: [textArr["date_format6"], textArr["date_format6"], textArr["date_format7"]],
				 month: [textArr["date_format2"], textArr["date_format2"], textArr["date_format3"]],
		  },
		  tickPositioner: function (min, max) {
          var xDataRange = max - min,
              positions = [],
              tick = min;

          positions.info = {higherRanks: {}};

          if (xDataRange <= 86400000) {
              // If range is 1 day max => 1 tick every hour
              increment = 3600000;
              positions.info.unitName = "hour";
              //$("#spotGraph1 .highcharts-markers").show();
          } else if (xDataRange > 86400000 && xDataRange <= 2678400000 + (86400000)) {
              // If range is between 1 day and 1 month => 1 tick every day
              increment = 86400000;
              positions.info.unitName = "day";
              //$("#spotGraph1 .highcharts-markers").hide();
          }else if (xDataRange > 2678400000 + (86400000) && xDataRange <= 31536000000) {
              // If range is between 1 month and 1 year => 1 tick every month
              increment = 2678400000;
              positions.info.unitName = "month";
              //$("#spotGraph1 .highcharts-markers").hide();
          } else {
              // If more than 1 year displayed, 1 tick every year
              increment = 365 * 24 * 60 * 60 * 1000;
              positions.info.unitName = "year";
              //$("#spotGraph1 .highcharts-markers").hide();
          }

          let period = $("#filter-section--period input:checked").val();
          // Create ticks
          for(tick = min; tick - increment < max; tick += increment) {
            if(window.matchMedia('screen and (max-width:1600px)').matches)
            {
              if(tick == min)
              {
	            	positions.push(tick);  
              }
              if(period == "year" && tick >= max - increment)
              {
	            	positions.push(max);  
              }
              else if(period == "month" && tick >= max - increment)
              {
	            	positions.push(max);  
              }
              else if(period == "5year" && tick >= max - increment)
              {
	              let maxDate = new Date(max);
	              let maxDateMonth = Number(maxDate.getMonth() + 1);
	              let maxYear = Number(maxDate.getFullYear());
	              if(maxDateMonth < 4)
	              {
		            	maxYear = maxYear - 1; 
	              }
	              maxDate = new Date(maxYear,3,1, 23,30);
	              console.log("maxDate",maxDate);
	            	positions.push(maxDate.getTime());  
              }
							else if(tick < max && tick >= max - increment)
              {
	            	positions.push(tick);  
              }
            }
            else
            {
              positions.push(tick);
            }
          }
          positions.info.totalRange = positions[positions.length - 1] - positions[0];
          return positions;
      }
	  },
		tooltip: { valueSuffix: '(kWh)',headerFormat: textArr["tooltip_format"], },
    rangeSelector: {
	    inputDateFormat: textArr["ymd"],
			inputEditDateFormat: textArr["ymd"],
      allButtonsEnabled: true,
      buttons: [ 
      {
		    type: 'hour',
		    count: 23.5,
		    text: '1d',
		    title: 'View 1 day'
			}, 
      {
		    type: 'hour',
		    count: setMonthTime(selectDate),
		    text: '1m',
		    title: 'View 1 month'
		}, {
		    type: 'year',
		    count: 1,
		    text: '1y',
		    title: 'View 1 year'
		}, {
		    type: 'year',
		    count: 5,
		    text: '5y',
		    title: 'View 5 year'
		}, 
		{
		    type: 'all',
		    text: 'All',
		    title: 'View all'
		}],
      selected: graphSelectedPeriod
    },
    legend: {
      enabled: true,
      align: 'right',
			verticalAlign: 'top',
			itemStyle: {
          color: 'black',
          fontFamily: 'メイリオ,sans-serif',
          fontWeight: 400,
      }
    },
    series:[{
			turboThreshold: 0,
      data: amountData,
      id: 'amountl_all',
      name: textArr["total_contracted"],
      lineWidth: 1,
      color: '#939393',
      dataGrouping: {
        approximation: function (groupData) {
          let average = getAverageData(groupData);
					return average;
        }
      }
    }],	      
    time: {
      timezoneOffset: (new Date).getTimezoneOffset()
    },
    responsive: {
        rules: [
/*
        	{
	        	condition: {
                maxWidth: 960
            },
					  chartOptions: {
						  xAxis: {
							  showLastLabel: true,
								dateTimeLabelFormats: {
				         hour: ['%H', '%H', '-%H'],
				         day: [textArr["date_format2"], textArr["date_format2"], textArr["date_format3"]],
				         month: [textArr["date_format2"], textArr["date_format2"], textArr["date_format3"]],
						  	}, 
							}
						}
        	},
*/
        	{
            condition: {
                maxWidth: 767
            },
	            chartOptions: {
		            chart: {
									marginTop: 25,
						    },
/*
		             xAxis: {
								  labels: {
							      style: {
							          fontSize: 10,
							      }	      
						      }
					      },
*/
					      yAxis: {
								  labels: {
							      style: {
							          fontSize: 10,
							      }	      
						      }
					      },
		            rangeSelector: {
							    inputPosition: {
							        align: 'left',
							        x: 0,
							        y: -20
							    },
							    buttonPosition: {
							        align: 'right',
							        x: 0,
							        y: 0
							    },
								},
                legend: {
	                	verticalAlign: 'bottom',
                    align: 'left',
                    itemStyle: {
						          color: 'black',
						          fontFamily: 'メイリオ,sans-serif',
											fontSize: 10,
							      }
                }
            }
        }]
    }
  });
	
	//約定件数
	let numberData = jsonArray.map(x => [x[0],Number(x[8])]);
	intradayGraphArr["number"] = Highcharts.stockChart('numberGraph_' + fileDate, {
     navigator: {
        adaptToUpdatedData: false,
    },
    credits: {
      enabled: false
    },
    chart: {
        type: 'column',
    },
    plotOptions: {
      column: {
          pointPadding: 0.2,
          borderWidth: 0
      },
      tooltip: {
      dateTimeLabelFormats: {
        millisecond: ['%Y/%m/%d %H:%M:%S.%L', '%Y/%m/%d %H:%M:%S.%L', '-%H:%M:%S.%L'],
         second: ['%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '-%H:%M:%S'],
         minute: [textArr["date_format"], textArr["date_format"], '-%H:%M'],
         hour: [textArr["date_format"], textArr["date_format"], '-%H:%M'],
         day: [textArr["date_format2"], textArr["date_format2"], textArr["date_format3"]],
         week: [textArr["date_format2"], textArr["date_format2"], textArr["date_format3"]],
         month: ['%B %Y', '%B', '-%B %Y'],
         year: ['%Y', '%Y', '-%Y']
      }
     }
		},
    yAxis: { 
	    title: {
		     align: 'high',
		     offset: 0,
		     rotation: 0,
         y: -10 
		  },
		  opposite: false
	  },
	  navigator: {
	     xAxis: {
		     	max: undefined,
					min: xAxisMinVal,
            dateTimeLabelFormats: {
		          day:  textArr["date_format4"],
		          week: textArr["date_format4"],
		          month:textArr["date_format4"],
		          year: textArr["date_format4"]
		        },
            labels: {
				      style: {
				          color: 'black',
				          fontFamily: 'Oswald',
				      }
			      },
        }
	  },
	  xAxis: {
		  max: xAxisMaxVal,
			min: xAxisMinVal,
			ordinal: false,
		  labels: {
	      style: {
	          color: 'black',
	          fontFamily: 'Oswald',
	      },  
	      formatter: function() {
		      console.log(Highcharts.dateFormat(this.dateTimeLabelFormat, this.value));
        return Highcharts.dateFormat(this.dateTimeLabelFormat, this.value);
      	},	  
      },
		  dateTimeLabelFormats: {
         hour: ['%H:%M', '%H:%M', '-%H:%M'],
				 day: [textArr["date_format6"], textArr["date_format6"], textArr["date_format7"]],
				 month: [textArr["date_format2"], textArr["date_format2"], textArr["date_format3"]],
		  },
		  tickPositioner: function (min, max) {
          var xDataRange = max - min,
              positions = [],
              tick = min;

          positions.info = {higherRanks: {}};

          if (xDataRange <= 86400000) {
              // If range is 1 day max => 1 tick every hour
              increment = 3600000;
              positions.info.unitName = "hour";
              //$("#spotGraph1 .highcharts-markers").show();
          } else if (xDataRange > 86400000 && xDataRange <= 2678400000 + (86400000)) {
              // If range is between 1 day and 1 month => 1 tick every day
              increment = 86400000;
              positions.info.unitName = "day";
              //$("#spotGraph1 .highcharts-markers").hide();
					}else if (xDataRange > 2678400000 + (86400000) && xDataRange <= 31536000000) {
              // If range is between 1 month and 1 year => 1 tick every month
              increment = 2678400000;
              positions.info.unitName = "month";
              //$("#spotGraph1 .highcharts-markers").hide();
          } else {
              // If more than 1 year displayed, 1 tick every year
              increment = 365 * 24 * 60 * 60 * 1000;
              positions.info.unitName = "year";
              //$("#spotGraph1 .highcharts-markers").hide();
          }

          let period = $("#filter-section--period input:checked").val();
          // Create ticks
          for(tick = min; tick - increment < max; tick += increment) {
            if(window.matchMedia('screen and (max-width:1600px)').matches)
            {
              if(tick == min)
              {
	            	positions.push(tick);  
              }
              if(period == "year" && tick >= max - increment)
              {
	            	positions.push(max);  
              }
              else if(period == "month" && tick >= max - increment)
              {
	            	positions.push(max);  
              }
              else if(period == "5year" && tick >= max - increment)
              {
	              let maxDate = new Date(max);
	              let maxDateMonth = Number(maxDate.getMonth() + 1);
	              let maxYear = Number(maxDate.getFullYear());
	              if(maxDateMonth < 4)
	              {
		            	maxYear = maxYear - 1; 
	              }
	              maxDate = new Date(maxYear,3,1, 23,30);
	              console.log("maxDate",maxDate);
	            	positions.push(maxDate.getTime());  
              }
							else if(tick < max && tick >= max - increment)
              {
	            	positions.push(tick);  
              }
            }
            else
            {
              positions.push(tick);
            }
          }
          positions.info.totalRange = positions[positions.length - 1] - positions[0];
          return positions;
      }
	  },
		tooltip: { headerFormat: textArr["tooltip_format"] },
    rangeSelector: {
	    inputDateFormat: textArr["ymd"],
			inputEditDateFormat: textArr["ymd"],
      allButtonsEnabled: true,
      buttons: [ 
      {
		    type: 'hour',
		    count: 23.5,
		    text: '1d',
		    title: 'View 1 day'
			}, 
      {
		    type: 'hour',
		    count: setMonthTime(selectDate),
		    text: '1m',
		    title: 'View 1 month'
		}, {
		    type: 'year',
		    count: 1,
		    text: '1y',
		    title: 'View 1 year'
		}, {
		    type: 'year',
		    count: 5,
		    text: '5y',
		    title: 'View 5 year'
		}, 
		{
		    type: 'all',
		    text: 'All',
		    title: 'View all'
		}],
      selected: graphSelectedPeriod
    },
    legend: {
      enabled: true,
      align: 'right',
			verticalAlign: 'top',
			itemStyle: {
          color: 'black',
          fontFamily: 'メイリオ,sans-serif',
          fontWeight: 400,
      }
    },
    series:[{
			turboThreshold: 0,
      data: numberData,
      id: 'amountl_all',
      name: textArr["number_of_contracts"],
      lineWidth: 1,
      color: '#939393',
      dataGrouping: {
        approximation: function (groupData) {
          let average = getAverageData(groupData);
					return average;
        }
      }
    }],	      
    time: {
      timezoneOffset: (new Date).getTimezoneOffset()
    },
    responsive: {
        rules: [
/*
        	{
	        	condition: {
                maxWidth: 960
            },
					  chartOptions: {
						  xAxis: {
							  showLastLabel: true,
								dateTimeLabelFormats: {
				         hour: ['%H', '%H', '-%H'],
				         day: [textArr["date_format2"], textArr["date_format2"], textArr["date_format3"]],
				         month: [textArr["date_format2"], textArr["date_format2"], textArr["date_format3"]],
						  	}, 
							}
						}
        	},
*/
        	{
            condition: {
                maxWidth: 767
            },
	            chartOptions: {
		            chart: {
									marginTop: 25,
						    },
/*
		             xAxis: {
								  labels: {
							      style: {
							          fontSize: 10,
							      }	      
						      }
					      },
*/
					      yAxis: {
								  labels: {
							      style: {
							          fontSize: 10,
							      }	      
						      }
					      },
		            rangeSelector: {
							    inputPosition: {
							        align: 'left',
							        x: 0,
							        y: -20
							    },
							    buttonPosition: {
							        align: 'right',
							        x: 0,
							        y: 0
							    },
								},
                legend: {
	                	verticalAlign: 'bottom',
                    align: 'left',
                    itemStyle: {
						          color: 'black',
						          fontFamily: 'メイリオ,sans-serif',
											fontSize: 10,
							      }
                }
            }
        }]
    }
  });
	
	if(dataStatus == "create")
	{
		let html =  "";
		if(selectDateVal)
		{
			
		}
		else
		{
			selectDateVal = moment(Math.max.apply(null, dateArr[fileDate])/1000,'X').format('YYYY/MM/DD');
		}
	  for (let i = 1; i <= Object.keys(intradayAllTableData[selectDateVal]).length; i++){
			let spotTime = moment(intradayAllTableData[selectDateVal][i][0][0]/1000,'X').format('HH:mm');
			let csv_next_unixtime = intradayAllTableData[selectDateVal][i][0][0] + (1800*1000);
			let spotNextTime = moment(csv_next_unixtime/1000,'X').format('HH:mm');
		  //約定価格
		  html += "<tr>";
			html += "<td>" + spotTime + "-" + spotNextTime + "</td>";
			for (let j = 2; j <= 8; j++){
				if(j == 7)
				{
					html += "<td class='cell--number'>" + setTableCell(intradayAllTableData[selectDateVal][i][0][j]) + "</td>";
				}
				else
				{
					html += "<td class='cell--number'>" + intradayAllTableData[selectDateVal][i][0][j] + "</td>";
				}
			}
			html += "</tr>";
		}
		$("#intraday__table .graph-section__table tbody").html(html);
	}
}

/*
function init()
{
	//最新のspotデータ
	dateArr[csvDateArr["intraday"]["latestYear"]] = new Array();
	getCSV("intraday",csvDateArr["intraday"]["latestYear"],"intraday","create");
}
*/

function checkSet5year(tradingYear,selectYear)
{
	let checkFlag = true;
	for (let year = tradingYear; year <= selectYear; year++) {
		if(!intradayAllData[year])
		{
				checkFlag = false;
		}
	}
	return checkFlag;
}

function set5year(selectYear,xAxisMax,period)
{
	intradayDataArrCount = 0;
	let intradayData5yArrCount = 0;
	let tradingYear = selectYear - 4;
	let jsonArray = new Array();
	if(tradingYear < csvDateArr["intraday"]["oldYear"])
	{
		tradingYear = csvDateArr["intraday"]["oldYear"];
	}
	console.log(Math.min.apply(null, dateArr[tradingYear]));
	let status = "update";
	for (let year = tradingYear; year <= selectYear; year++) {
		if(!intradayAllData[year])
		{
			dateArr[year] = new Array();
			intradayData5yArrCount = intradayData5yArrCount + 1;	
			status = "create";
		}
	}
	if(status == "create")
	{
		for (let year = tradingYear; year <= selectYear; year++) {
			if(!intradayAllData[year])
			{
				getCSV("intraday",year,"intraday",undefined,undefined,"5year",intradayData5yArrCount,selectYear,xAxisMax);		
			}
		}
	}
	else
	{
		let jsonArray = new Array();
		if(tradingYear < csvDateArr["intraday"]["oldYear"])
		{
			tradingYear = csvDateArr["intraday"]["oldYear"];
		}
		console.log(Math.min.apply(null, dateArr[tradingYear]));
		let xAxisMin = Math.min.apply(null, dateArr[tradingYear]);
		for (let year = tradingYear; year <= selectYear; year++) {
			console.log(intradayAllData[year]);
			jsonArray = jsonArray.concat(intradayAllData[year]);
		}
		console.log("jsonArray",jsonArray);
		console.log("xAxisMin",xAxisMin);
		$(".graph-section__content").addClass("period5Y");
		setGrafhPrice(jsonArray,selectYear,xAxisMax,xAxisMin);				
	}
}
 
$(function(){
	setGrafhCalendar();
	
	let updatedOptions;
	 
	/* 表示期間変更 */
	$("#filter-section--period input").on("change",function(){		 
	 let period = $(this).val();
	 let $periodLabel = $(this).parent(".filter-label");
	 let selectedPeriod;
	 let yyyy;
	 
	 if($(this).prop("checked") == true)
	 {
			$("#filter-section--period .filter-label").not($periodLabel).removeClass("active");
			$periodLabel.addClass("active");
			let trading_date = $('#datepicker').datepicker('getDate');
			let selectDate = moment(trading_date).format('YYYY/MM/DD');
			let trading_date_time;
			let delivery_date = new Date(trading_date.getFullYear(), trading_date.getMonth(), trading_date.getDate() ,23,30);
			console.log(delivery_date);
			let delivery_date_time = delivery_date.getTime();		
			let minDate;
			if(period != "5year")
			{
				minDate = Math.min.apply(null, dateArr[trading_date.getFullYear()]);
			}			
			switch (period) {
			  case "day":
			    selectedPeriod = 0;
			    break
			  case "month":
			    selectedPeriod = 1;
			    if(compareMonthDay(selectDate))
			    {
						trading_date = new Date(trading_date.getFullYear(), trading_date.getMonth(), 1);
			    }
			    else
			    {
				    trading_date = new Date(trading_date.getFullYear(), trading_date.getMonth() - 1, trading_date.getDate(), trading_date.getHours());
			    }
			    break
			  case "year":
			    selectedPeriod = 2;
			    trading_date = new Date(trading_date.getFullYear() - 1, trading_date.getMonth(), trading_date.getDate(), trading_date.getHours());
			    break
			  case "5year":
			    selectedPeriod = 3;
			    trading_date = new Date(trading_date.getFullYear() - 5, trading_date.getMonth(), trading_date.getDate(), trading_date.getHours());
			    break
			  default:
					selectedPeriod = 1;    
			}
				
			updatedOptions = {
			 	rangeSelector: {
					 selected: selectedPeriod
				}	
			}
			
			yyyy = delivery_date.getFullYear();
			if((delivery_date.getMonth() + 1) < 4)//1〜3月の場合
			{
				console.log("trading_date",trading_date);
				minDate = Math.min.apply(null, dateArr[delivery_date.getFullYear() - 1]);
				yyyy = delivery_date.getFullYear() - 1; 
			}
			trading_date_time = trading_date.getTime();	
			
			if(trading_date_time < minDate)
			{
				trading_date_time = minDate;	
			}
			
			let selectYear = yyyy;
			let xAxisMax = delivery_date_time;
			if(period == "5year")
			{
				$(".graph-section__content").addClass("period5Y");
				$("#priceGraph").html("");
				$("#amountGraph").html("");
				$("#numberGraph").html("");
				set5year(selectYear,xAxisMax,period,selectDate);
			}
			else
			{
				if($(".graph-section__content").hasClass("period5Y"))
				{
					let jsonArray = intradayAllData[selectYear];
					$(".graph-section__content").removeClass("period5Y");
					$("#priceGraph").html("");
					$("#amountGraph").html("");
					$("#numberGraph").html("");
					window.setTimeout(function(){
					 setGrafhPrice(jsonArray,selectYear,xAxisMax,undefined,undefined,selectDate);
					}, 500);
				}
				else
				{
					intradayGraphArr["price"].update(updatedOptions, true, true);
					intradayGraphArr["amount"].update(updatedOptions, true, true);	
					intradayGraphArr["number"].update(updatedOptions, true, true);
					intradayGraphArr["price"].xAxis[0].setExtremes(trading_date_time,delivery_date_time);
					intradayGraphArr["amount"].xAxis[0].setExtremes(trading_date_time,delivery_date_time);
					intradayGraphArr["number"].xAxis[0].setExtremes(trading_date_time,delivery_date_time);
					intradayGraphArr["price"].redraw();
					intradayGraphArr["amount"].redraw();
					intradayGraphArr["number"].redraw();
				}
			}
		}
	});
	 
  /* 表示タイプ */
  $("#filter-section--type .button").on("click",function(){
		let type = $( this).data("type");
		$(this).addClass("active");
		$("#filter-section--type .button").not(this).removeClass("active");
		if(type == "graph")
		{
			$(".graph-section").show();
			$(".table-section").hide();  
			$("#filter-section--period").removeClass("disabled"); 
		}
		else
		{
			$(".graph-section").hide();
			$(".table-section").show();  
			$("#filter-section--period").addClass("disabled"); 
		}
	});
	
	//データダウンロード(Init)
	$("#data-area__filter .dl-button").on("click",function(){
		if($(this).hasClass("init"))
		{
			let file = $(this).data("dl");
			getGraphDate("intraday","download",file);
		}
	});
	
	//カレンダー表示
	$("#button--calender-show").on("click",function(){
		$("#datepicker-area").fadeIn();
	});
});	

