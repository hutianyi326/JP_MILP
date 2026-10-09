// CSVファイル
const conDataFileDir = 'csv';
const conDemandCommentDir = 'demand_comment';
const conProcurementRecordDir = 'procurement_record';
const conOperationRecordDir = 'operation_record';
const conReserveItemsDir = 'reserve_items';

/**
 * 現時刻の取得
 */
function currentTime() {
	let ret = new Date().getTime();
	// 末尾から5文字を削除
	ret =  ret.toString().slice(0, -5);
	return ret;
}

/**
 * エンティティリストの作成
 * @param stIdx
 * @memo グラフデータは、0行目破棄
 */
function createHashFromArySt(keys, ary, stIdx){
	let st = parseInt(stIdx);
	let obj = {};
	let x_cnt = ary[st].length;
	for(let y = st; y<ary.length; y++){
		let ent = {};
		for(let x = 0; x<x_cnt; x++){
			ent[keys[x]] = ary[y][x];
		}
		obj[y] = ent;
	}
	return obj;
}

/**
 * 配列の作成
 */
function csvSplit(dataArr){
    let arr =[];
    let list = dataArr.split('\n');
    for(let i = 0; i <list.length; i++){
        arr[i] = list[i].split(',');
    }
    return arr;
}

/**
 * ファイル場所の取得
 */
function getFilePlace(fileNm, conFlDir, fileExtension = ".csv") {
	let extension = fileExtension + "?" + currentTime();
	let placeNm = conFlDir + fileNm  + extension;
    return placeNm;
}
/**
 * @memo グラフ
 * @param 日付
 */
function getFileNmGraph(date) {
	let fileNm = "/eria_kyokyujisseki_" + date;
	return getFilePlace(fileNm, conDataFileDir);
}
/**
 * @memo 燃料テーブルリスト
 */
function getFileNmTblFuel() {
	let fileNm = "/eria_jukyu_nendo_list";
	return getFilePlace(fileNm, conDataFileDir);
}

/**
 * ファイル名の取得
 * @memo 燃料テーブルリンク
 * @param ファイル名(拡張子付)
 */
function getFileNmLink(val) {
	let fileNm = "/" + val + "?" + currentTime();
	let placeNm = conDataFileDir + fileNm;
	return placeNm;
}

/**
 * ファイル名の取得
 * @memo 前日テーブル/過去テーブル
 * @param 日付
 */
function getFileNmTblUnit(date) {
	let fileNm = "/bghatsu_09_" + date;
	return getFilePlace(fileNm, conDataFileDir);
}

/**
 * ファイル名の取得
 * @memo 過去テーブル
 */
function getFileNmTblUnitKakoList() {
	let fileNm = "/bghatsu_09_kako_list";
	return getFilePlace(fileNm, conDataFileDir);
}

/**
 * ファイル名の取得
 * @memo 調達実績リスト
 */
function getFileNmProcurementRecord() {
	let fileNm = "/procurementrecordlist";
	return getFilePlace(fileNm, conProcurementRecordDir);
}

/**
 * ファイル名の取得
 * @memo 運用実績リンク名
 */
function getFileNmOperationRecord() {
	let fileNm = "/operperf";
	return getFilePlace(fileNm, conOperationRecordDir, ".txt");
}

/**
 * ファイル名の取得
 * @memo 需給関連情報コメント
 */
function getFileNmDemandComment() {
	let fileNm = "/comment";
	return getFilePlace(fileNm, conDemandCommentDir, ".txt");
}

/**
 * ファイル名の取得
 * @memo 需給関連情報PDFリンク名
 */
function getFileNmDemandPdf() {
	let fileNm = "/pdf";
	return getFilePlace(fileNm, conDemandCommentDir, ".txt");
}

/**
 * ファイル名の取得
 * @memo 予備項目リスト
 */
function getFileNmReserveItems() {
	let fileNm = "/reserveItems";
	return getFilePlace(fileNm, conReserveItemsDir, ".txt");
}

/**
 * 数値チェック
 */
function isNumber(val){
	var regexp = new RegExp(/^[0-9]+(\.[0-9]+)?$/);
	return regexp.test(val);
}

/**
 * 半角ハイフンチェック
 */
function isNotHyphen(val){
	// 前方一致
	if(setDelYen(val).indexOf('-') != 0){
		return true;
	}
	return false;
}

/**
 * undefined変換
 * @return 半角ハイフン
 */
function setUndef(val){
	let ret = val;
	if (val === undefined) {
		ret = '-';
	}
	return ret;
}

/**
 * 改行コード削除
 */
function setDelYen(val){
	let ret = val;
	ret = String( val ).replace(/\r?\n/g, '');
	return ret;
}

/**
 * 日付0埋め
 */
function setAdigit(val){
	let ret  = val;
	ret = ('0' + val).slice(-2);
	return ret;
}

/**
 * 今日の取得
 * @return 今日日付フォーマット済み（yyyymmdd）
 */
function getToday(){
	let today = new Date();
	let year = today.getFullYear();
	let month = today.getMonth() + 1;
	let day = today.getDate();
    let ret = year + setAdigit(month) + setAdigit(day);
	return ret;
}

/**
 * 	昨日の取得
 * @return 昨日日付フォーマット済み（yyyymmdd）
 */
function getYest(){
	let yeat = new Date();
	yeat.setDate(yeat.getDate() - 1);
	let year = yeat.getFullYear();
	let month = yeat.getMonth() + 1;
	let day = yeat.getDate();
    let ret = year + setAdigit(month) + setAdigit(day);
	return ret;
}

/**
 * 	日付指定での取得
 * @return 指定日付フォーマット済み（yyyymmdd）
 */
function getSpecifyDate(Specify = 0){
	let yeat = new Date();
	yeat.setDate(yeat.getDate() + Specify);
	let year = yeat.getFullYear();
	let month = yeat.getMonth() + 1;
	let day = yeat.getDate();
    let ret = year + setAdigit(month) + setAdigit(day);
	return ret;
}

/**
 * 初期の設定
 */
function setLoadSt() {
	setDispCom(1, getFileNmGraph(getToday()));
	setDispCom(2, getFileNmTblFuel());
	setDispCom(3, getFileNmTblUnit(getYest()));
	setDispCom(4, getFileNmProcurementRecord());
	setDispCom(5, getFileNmOperationRecord());
	setDispCom(6, getFileNmDemandComment());
	setDispCom(7, getFileNmReserveItems());
}

/**
 * 共通
 * 表示の設定
 * @pram dataKbn(1:graph、2:tblFuel、3:tblUnit、4:procurementRecord、5:operationRecord、6:demandComment、7:reserveItems)
 */
function setDispCom(dataKbn, data) {
	var ret = false;
    let xhr = new XMLHttpRequest(); 
    xhr.open("GET",data,true);
    xhr.onload = function (e) {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                let responce = xhr.responseText;
				ret = true;
				if(dataKbn == 1){
	            	csvArrGraph(responce);
				}else if(dataKbn == 2){
					csvArrTblFuel(responce);
				}else if(dataKbn == 4){
					csvArrListProcurementRecord(responce);
				}else if(dataKbn == 5){
					txtOperationRecord(responce);
				}else if(dataKbn == 6){
					ret = txtDemandComment(responce);
				}else if(dataKbn == 7){
					txtReserveItems(responce);
				}
            } else {
				ret = false;
            }
        }
		setOutputCom(dataKbn, ret);
    };
	xhr.send(null);
}

/**
 * 共通
 * 画面出力の設定
 * @pram dataKbn(1:graph、2:tblFuel、3:tblUnit、4:procurementRecord、5:operationRecord、6:demandComment、7:reserveItems)
 * @pram ret ファイル有無
 */
function setOutputCom(dataKbn, ret){
	if(dataKbn == 1){
		if (ret){
			setOutputGraph(ret);
		} else {
			//当日ファイルが存在しないため前日ファイルを取得
			getFileYestGraph(ret);
		}
	}else if(dataKbn == 2){
		setOutputFuel(ret);
	}else if(dataKbn == 3) {
		getFileUnitKakoList(ret);
	}else if(dataKbn == 4) {
		setOutputProcurementRecord(ret);
	}else if(dataKbn == 6) {
		getFileDemandPdfLink(ret);
	}
}

/**
 * グラフ
 * 前日ファイルの取得
 */
function getFileYestGraph(ret){
	let yestGraph = getFileNmGraph(getYest());
	let xhr = new XMLHttpRequest();
	xhr.open("GET",yestGraph,true);
	xhr.onload = function (e) {
		if (xhr.readyState === 4) {
			if (xhr.status === 200) {
				let responce = xhr.responseText;
				ret = true;
				csvArrGraph(responce);
			}
		}
		setOutputGraph(ret);
	}
	xhr.send(null);
}

/**
 * グラフ
 * 画面出力の設定
 */
function setOutputGraph(ret){
	if(ret){
		$('#outputGraph').show();
		$('#outputNoGraph').hide();
	} else {
		$('#outputGraph').hide();
		$('#outputNoGraph').show();
	}
	document.getElementById('chartSetdt').style.visibility ="visible";
}

/**
 * グラフ
 * csvデータの取得
 */
function csvArrGraph(dataArr){
	let arr = csvSplit(dataArr);
	let keys = ['date','time',"fuel1","fuel2","fuel3","fuel4","fuel5","fuel6","fuel7","fuel8","fuel9","fuel10","fuel11","fuel12","fuel13","fuel14","areaDd"];
	let hash = createHashFromArySt(keys, arr, 1);
	createDispGraph(hash, keys);
}

/**
 * グラフ
 * 数値補完
 * @note isfalse0
 */
function setiNum(val) {
	let ret = Number(0);
	if(isNumber(val)){
	    ret = Number(val);
	}
	return ret;
}

/**
 * グラフ
 * ダブルクォーテーションの削除
 * @note 先頭と末尾の削除
 */
function setAryDt(val){
	let ret = val;
	for (let n in ret) {
		let str = ret[n];
		if(str){
//			str = str.slice(1);
//			str = str.slice(0,-1);
      str = str.replace(/\r/g, '');
      str = str.replace(/\"/g, '');
			ret[n] = str;
		}
	}
	return  ret;
}

/**
 * グラフ
 * Y軸合計の最大値を取得
 */
function getYjikuMax(hash, keys){
	let totalAry = [];
	let retMax = 0;
	for(var i in hash){
		let rowSum = 0;
		// ２行目から(ヘッダ行除外)
		if(i > 1 ){
			var ent = hash[i];
			for (let j = 2; j < keys.length -1 ; j++) {
				rowSum += setiNum(ent[keys[j]]);
			}
			totalAry.push(rowSum);
		}
	}
	// 行合計最大値
	let max = totalAry.reduce(function (a, b) {
		return Math.max(a, b);
	});
	// Y軸最高値を計算（100単位切り上げ）
	retMax =  Math.ceil(max / 100) * 100
	return retMax;
}

/**
 * グラフ
 * グラフの生成
 */
function createDispGraph(hash, keys){
	let xTime = ['00','','01','','02','','03','','04','','05','','06','','07','','08','','09','','10','','11','','12','','13','','14','','15','','16','','17','','18','','19','','20','','21','','22','','23','','24'];
	let fuelType_1 = [];
	let fuelType_2 = [];
	let fuelType_3 = [];
	let fuelType_4 = [];
	let fuelType_5 = [];
	let fuelType_6 = [];
	let fuelType_7 = [];
	let fuelType_8 = [];
	let fuelType_9 = [];
	let fuelType_10 = [];
	let fuelType_11 = [];
	let fuelType_12 = [];
	let fuelType_13 = [];
	let fuelType_14 = [];
	let areaDemand = [];

	for(var i in hash){
		// ２行目から(ヘッダ行除外)
		if(i > 1 ){
			var ent = setAryDt(hash[i]);
            fuelType_1.push(setiNum(ent[keys[2]]));
        	fuelType_2.push(setiNum(ent[keys[3]]));
        	fuelType_3.push(setiNum(ent[keys[4]]));
        	fuelType_4.push(setiNum(ent[keys[5]]));
        	fuelType_5.push(setiNum(ent[keys[6]]));
        	fuelType_6.push(setiNum(ent[keys[7]]));
        	fuelType_7.push(setiNum(ent[keys[8]]));
        	fuelType_8.push(setiNum(ent[keys[9]]));
        	fuelType_9.push(setiNum(ent[keys[10]]));
        	fuelType_10.push(setiNum(ent[keys[11]]));
        	fuelType_11.push(setiNum(ent[keys[12]]));
        	fuelType_12.push(setiNum(ent[keys[13]]));
        	fuelType_13.push(setiNum(ent[keys[14]]));
        	fuelType_14.push(setiNum(ent[keys[15]]));
        	areaDemand.push(setiNum(ent[keys[16]]));
		}
	}
	// // Y軸の最大値の算出
	// let sumMax = getYjikuMax(hash, keys);
	// Y軸は2000固定とする
	let sumMax = 2000;
    let ctx = document.getElementById("myAreaChart");
    let myAreaChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: xTime,
            datasets: [
				// エリア需要
                {
                    fill: false, // 塗らない
                    data: areaDemand,
                    yAxisID: 'y-2',
                    lineTension:0.2, //直線
                    tension:0, //直線
                    borderWidth:2,
                    borderColor: "rgba(255,0,0,1)",
                    backgroundColor: "rgba(255,0,0,1)",
                },
                // 原子力
                {
                    fill: 'origin', //'origin'まで塗る
                    data: fuelType_1,
                    yAxisID: 'y-1',
                    lineTension:0.2,
                    borderWidth:1,
                    borderColor: "rgba(75,0,130,1)",
                    backgroundColor: "rgba(75,0,130,1)"
                },
                // 地熱
                {
                    fill: 1,
                    data: fuelType_2,
                    yAxisID: 'y-1',
                    lineTension:0.2,
                    borderWidth:1,
                    borderColor: "rgba(128,0,0,1)",
                    backgroundColor: "rgba(128,0,0,1)"
                },
                // 水力
                {
                    fill: 2, 
                    data: fuelType_3,
                    yAxisID: 'y-1',
                    lineTension:0.2,
                    borderWidth:1,
                    borderColor: "rgba(65,105,225,1)",
                    backgroundColor: "rgba(65,105,225,1)"
                },
				// 火力ＬＮＧ
                {
                    fill: 3, 
                    data: fuelType_4,
                    yAxisID: 'y-1',
                    lineTension:0.2,
                    borderWidth:1,
                    borderColor: "rgba(250,128,114,1)",
                    backgroundColor: "rgba(250,128,114,1)"
                },
				// 火力石炭
                {
                    fill: 4, 
                    data: fuelType_5,
                    yAxisID: 'y-1',
                    lineTension:0.2,
                    borderWidth:1,
                    borderColor: "rgba(211,211,211,1)",
                    backgroundColor: "rgba(211,211,211,1)"
                },
				// 火力石油
                {
                    fill: 5, 
                    data: fuelType_6,
                    yAxisID: 'y-1',
                    lineTension:0.2,
                    borderWidth:1,
                    borderColor: "rgba(255,228,181,1)",
                    backgroundColor: "rgba(255,228,181,1)"
                },
				// 火力その他
                {
                    fill: 6, 
                    data: fuelType_7,
                    yAxisID: 'y-1',
                    lineTension:0.2,
                    borderWidth:1,
                    borderColor: "rgba(100,149,237,1)",
                    backgroundColor: "rgba(100,149,237,1)"
                },
				// バイオマス
                {
                    fill: 7, 
                    data: fuelType_8,
                    yAxisID: 'y-1',
                    lineTension:0.2,
                    borderWidth:1,
                    borderColor: "rgba(50,205,50,1)",
                    backgroundColor: "rgba(50,205,50,1)"
                },
				// 風力
                {
                    fill: 8, 
                    data: fuelType_9,
                    yAxisID: 'y-1',
                    lineTension:0.2,
                    borderWidth:1,
                    borderColor: "rgba(0,128,0,1)",
                    backgroundColor: "rgba(0,128,0,1)"
                },
				// 太陽光
                {
                    fill: 9, 
                    data: fuelType_10,
                    yAxisID: 'y-1',
                    lineTension:0.2,
                    borderWidth:1,
                    borderColor: "rgba(255,255,0,1)",
                    backgroundColor: "rgba(255,255,0,1)"
                },
				// 揚水発電
                {
                    fill: 10, 
                    data: fuelType_11,
                    yAxisID: 'y-1',
                    lineTension:0.2,
                    borderWidth:1,
                    borderColor: "rgba(0,191,255,1)",
                    backgroundColor: "rgba(0,191,255,1)"
                },
				// 蓄電池
                {
                    fill: 11, 
                    data: fuelType_12,
                    yAxisID: 'y-1',
                    lineTension:0.2,
                    borderWidth:1,
                    borderColor: "rgba(255,140,0,1)",
                    backgroundColor: "rgba(255,140,0,1)"
                },
				// 連系線受電
                {
                    fill: 12, 
                    data: fuelType_13,
                    yAxisID: 'y-1',
                    lineTension:0.2,
                    borderWidth:1,
                    borderColor: "rgba(105,105,105,1)",
                    backgroundColor: "rgba(105,105,105,1)"
                },
				// その他
                {
                    fill: 13, 
                    data: fuelType_14,
                    yAxisID: 'y-1',
                    lineTension:0.2,
                    borderWidth:1,
                    borderColor: "rgba(199,21,133,1)",
                    backgroundColor: "rgba(199,21,133,1)"
                }
               
            ]
        },
        options: {
 		legend: {
			display: false // 凡例非表示
			},
		    tooltips : {
				enabled: false,	// ツールチップ非表示
		    },
			responsive: true,
		    elements: {
		    	point:{
		    		radius: 0 // ポインタ非表示
		    	}
		    },
		    plugins : {
		    	filler : {
		        	propagate : true // 塗りつぶし伝播
		      	}
		    },
			scales: {
                xAxes: 
                [{
                  scaleLabel: 
                  {   // 軸ラベル
                     display: true,
                     labelString: "(時間)"
                  },
                  stacked: true, // 積み上げ有効
                  display: true,
                  ticks: {
                    autoSkip: true,
                    maxTicksLimit: 28 // 値の最大表示数
			            }
                }],
                yAxes: 
                [{
                  scaleLabel: 
                  {   // 軸ラベル
                     display: true,
                     labelString: "(万Kw)"
                  },
                  id: 'y-1',
                  stacked: true, // 積み上げ有効
                  type: 'linear',
                  display: true,
                  position: 'left',
                  ticks: 
                  {
                    beginAtZero: true, // 0から
                    min: 0,
                    max: sumMax,
                    callback: function(label, index, labels) 
                    {
                      return label.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
                    } // 3桁カンマ
                   },
                  },
                  {
                    id: 'y-2',
                    stacked: false, // 積み上げ無効
                    type: 'linear',
                    display: false,	// 非表示
                    position: 'right',
                    ticks: 
                    {
                      beginAtZero: true, // 0から
                      min: 0,
                      max: sumMax
                    },
                    gridLines: 
                    {
                      drawOnChartArea: false, // 右の罫線は非表示（左で表示）
                    },
                   },
{
                    id: 'y-3',
                    stacked: false, // 積み上げ無効
                    type: 'bar',
                    display: false,	// 非表示
                    legend: {
                      position: 'bottom'
                    },  
                    ticks: 
                    {
                      beginAtZero: true, // 0から
                      min: 0,
                      max: sumMax
                    },
                    gridLines: 
                    {
                      drawOnChartArea: false, // 右の罫線は非表示（左で表示）
                    },
                   },]
               }
           }
    });
}

/**
 * 燃料
 * 画面出力の設定
 */
function setOutputFuel(ret){
	if(ret){
		$('#outputTblFuel').show();
        $('#outputNoTblFuel').hide();
	} else {
		$('#outputTblFuel').hide();
        $('#outputNoTblFuel').show();
	}
	document.getElementById('tableSetdt').style.visibility ="visible";
}

/**
 * 燃料
 * csvデータの取得
 */
function csvArrTblFuel(dataArr){
	let keysFuel = ['nendo','mo4',"mo5","mo6","mo7","mo8","mo9","mo10","mo11","mo12","mo1","mo2","mo3"];
	let arr = csvSplit(dataArr);
	let hash = createHashFromArySt(keysFuel, arr, 0);
	createDispTblFuel(hash, keysFuel);
}

/**
 * 燃料
 * テーブル設定値を取得
 * @pram csvデータ
 */
function getTblValFuel(val){
	let ret = val;
	if(isNotHyphen(val)){
		let placeNm = getFileNmLink(val);
		ret = '<a class="n_icon_excel" href="'+ placeNm + '" target="_blank" style="opacity: 1;"><img class="n_icon" alt="csvファイル" src="/library/td/images/icon/icon_excel.png">csv</a>';
	}
	return ret;
}

/**
 * 燃料
 * テーブルの生成
 */
function createDispTblFuel(hash, keys){
 	let header = ['年度', '４月', '５月', '６月', '７月', '８月', '９月', '10月', '11月', '12月', '１月', '２月', '３月'];
	let outputTblFuel = $('#outputTblFuel');
    outputTblFuel.empty();
	let len = Object.keys(hash).length;
	let tableTag = $("<table></table>");
	let tbodyTag = $("<tbody></tbody>");
	// テーブル作成
	for(let a=0; a<len+1 ; a++){
		let trTag = $("<tr></tr>");
		for(let b=0; b<keys.length; b++){
			// ヘッダ行
			if(a == 0){
				let thTag = $("<th></th>");
				thTag.addClass("header n_align_center");
				thTag.text(header[b]);
				trTag.append(thTag);
			} else {
				var ent = hash[a-1];
				var v = setUndef(ent[keys[b]]);
				let tdTag = $("<td></td>");
				tdTag.addClass("n_align_center");

				// 年度列
				if(b == 0){
		        	tdTag.text(v);
				} else {
		        	tdTag.append(getTblValFuel(v));
				}
				trTag.append(tdTag);
			}
		}
		tbodyTag.append(trTag);
	}
	tableTag.append(tbodyTag);
	outputTblFuel.append(tableTag);
}

/**
 * 過去テーブルデータ取得
 */
function getFileUnitKakoList(ret){
	let unitKakoListNm = getFileNmTblUnitKakoList();
	var dateList = [];
	var yestDateList = [];
	let xhr = new XMLHttpRequest(); 
	xhr.open("GET",unitKakoListNm,true);
	xhr.onload = function (e) {
		if (xhr.readyState === 4) {
			if (xhr.status === 200) {
				responce = xhr.responseText;
				if (responce != "") {
					const tmpList = responce.split('\n');
					const tmpToday = getToday();
					const tmpYest = getYest();
					const tmpTwoDaysAgo = getSpecifyDate(-2);
					for (i = 0; i < tmpList.length; i++) {
						const date = tmpList[i].substr( 11, 8 );
						if (date != "") {
							// 過去データ日付リスト（当日・前日・前々日は除外）
							if (date != tmpToday && date != tmpYest && date != tmpTwoDaysAgo) {
								dateList.push(date);
							}
							// 前日データ日付リスト（前日・前々日が該当）
							if (date == tmpYest || date == tmpTwoDaysAgo) {
								yestDateList.push(date);
							}
						}
					}
				}
			}
		}
		createDispTblUnit(yestDateList , dateList);
	};
	xhr.send(null);
}

/**
 * 前日・過去
 * テーブルの生成
 * @param yestDateList 前日データ日付リスト
 * @param dateList 過去データ日付リスト
 */
function createDispTblUnit(yestDateList , dateList){
	//前日データ作成
	let outputTblUnit = $('#outputTblUnit');
    outputTblUnit.empty();
	let tableTag = $("<table></table>");
	let tbodyTag = $("<tbody></tbody>");
	let trTag = $("<tr></tr>");
	let thTag = $("<th></th>");
	thTag.text("前日データ");
	trTag.append(thTag);
	let tdTag = $('<td></td>');
	let getItem = "-";
	// 前日データ日付を取得（優先度：前日⇒前々日）
	if (yestDateList.length > 0) {
		yestDateList.sort(function(a, b) {return b - a;});
		yestDate = yestDateList[0];
		getItem = getTblValUnitKako(yestDate);
	}
	tdTag.append(getItem);
	trTag.append(tdTag);
	tbodyTag.append(trTag);

	//過去データ作成
	if (dateList.length > 0) {
		dataListCount = dateList.length;
		if (dataListCount > 10) {
			// 過去データ表示件数は最大10件まで
			dataListCount = 10;
		}
		for(let i = 0; i < dataListCount; i++){
			let trTagOld = $("<tr></tr>");
			if (i === 0) {
				let thTagOld = $('<th rowspan="' + dateList.length + '"></th>');
				thTagOld.text("過去データ（データ差替え分）");
				trTagOld.append(thTagOld);
			}

			let tdTagOld = $('<td></td>');
			let getItemOld = getTblValUnitKako(dateList[i]);
			tdTagOld.append(getItemOld);
			trTagOld.append(tdTagOld);
			tbodyTag.append(trTagOld);
		}
	} else {
		let trTagOld = $("<tr></tr>");
		let thTagOld = $('<th></th>');
		thTagOld.text("過去データ（データ差替え分）");
		trTagOld.append(thTagOld);
		let tdTagOld = $('<td></td>');
		let getItemOld = "-";
		tdTagOld.append(getItemOld);
		trTagOld.append(tdTagOld);
		tbodyTag.append(trTagOld);
	}

	tableTag.append(tbodyTag);
	outputTblUnit.append(tableTag);
}

/**
 * 過去
 * テーブル設定値を取得
 * @param date 過去データの日付
 */
function getTblValUnitKako(date){
	let ret = "-";
	let placeNm = getFileNmTblUnit(date);
	ret = '<a class="n_icon_excel" href="'+ placeNm + '" target="_blank" style="opacity: 1;"><img class="n_icon" alt="csvファイル" src="/library/td/images/icon/icon_excel.png">' + date + '</a>';
	return ret;
}


/**
 * 調達実績
 * csvデータの取得
 */
function csvArrListProcurementRecord(dataArr){
	let arr = csvSplit(dataArr);
	createDispListProcurementRecord(arr);
}


/**
 * 調達実績
 * リストの生成
 */
function createDispListProcurementRecord(arr){
	let outputListJisseki = $('#outputListProcurementRecord');
	outputListJisseki.empty();
	let divTag = $("<div></div>");
	for(let a = 0; a < arr.length; a++){
		if (arr[a][0] == "" || arr[a][0] == undefined) {
			continue;
		}

		let pTag = $("<p></p>");
		pTag.addClass("mb0");

		// ファイル名取得
		let fileNm = arr[a][0];
		let fileNmNengetu = fileNm.toString().substring( 0, 6 );
		let fileNmPath = getFilePlace("/" + fileNm, conProcurementRecordDir, "");

		// リンク作成
		let aTag = $("<a></a>");
		aTag.addClass("n_icon_excel");
		aTag.attr('href', fileNmPath);
		aTag.attr('target', "_blank");
		aTag.attr('style', "opacity: 1;");

		// Excel画像作成
		let imgTag = $("<img></img>");
		imgTag.addClass("n_icon");
		imgTag.attr('src', "/library/td/images/icon/icon_excel.png");
		imgTag.attr('alt', "Excelファイル");

		let txtDate = fileNmNengetu.substring( 0, 4 ) + "年" + fileNmNengetu.substring( 4, 6 ).replace(/^0+/, '') + "月";
		aTag.append(imgTag);
		aTag.append(txtDate);
		pTag.append(aTag);
		divTag.append(pTag);
	}
	outputListJisseki.append(divTag);
}

/**
 * 調達実績データ
 * 画面出力の設定
 */
function setOutputProcurementRecord(ret){
	if(ret){
		$('#outputListProcurementRecord').show();
	} else {
		$('#outputListProcurementRecord').hide();
	}
}

/**
 * 揚水発電所　運用実績データ
 * PDFリンクの取得
 */
function txtOperationRecord(responce){
	let pastFileNm = "";
	let thisFileNm = "";

	// PDFファイル名を取得
	let arrPdf = responce.split(/\n/);
	arrPdf.forEach(element => {
		if (element.substring(0,6) == "[past]") {
			pastFileNm = element.replace("[past]", "");
		} else if (element.substring(0,6) == "[this]") {
			thisFileNm = element.replace("[this]", "");
		}
	});
	setOutputOperationRecord(pastFileNm, thisFileNm);
}

/**
 * 揚水発電所　運用実績データ
 * 画面出力の設定
 */
function setOutputOperationRecord(pastFileNm, thisFileNm){

	// 過去実績
	let linkOperationRecordOld = document.getElementById('linkOperationRecordOld');
	let fileNmOperationRecordOld = getFilePlace("/" + pastFileNm, conOperationRecordDir, "");
	//href属性の値を書き換える
	linkOperationRecordOld.setAttribute('href', fileNmOperationRecordOld);

	// 今年度実績
	let linkOperationRecordNow = document.getElementById('linkOperationRecordNow');
	let fileNmOperationRecordNow = getFilePlace("/" + thisFileNm, conOperationRecordDir, "");
	//href属性の値を書き換える
	linkOperationRecordNow.setAttribute('href', fileNmOperationRecordNow);

}

/**
 * 需給関連情報コメント
 * トップページコメントの取得
 */
function txtDemandComment(responce){
	// 改行コードを<br>に置換
	let txtComment = responce.split(/\n/).join('<br>');
	if (txtComment) {
		createDispDemandComment(txtComment);
		return true;
	} else {
		// ファイル内部が空白の場合は、非公開とする
		return false;
	}
}

/**
 * 需給関連情報コメント
 * トップページコメントの生成
 */
function createDispDemandComment(txtComment){
	let demandCommentText = $('#demand_comment_text');
	demandCommentText.empty();
	let pTag = $("<p></p>");
	pTag.addClass("mb0");
	pTag.addClass("mt0");
	pTag.append(txtComment);
	demandCommentText.append(pTag);
}

/**
 * 需給関連情報PDFリンク
 * ファイル取得
 */
function getFileDemandPdfLink(ret){
	let fileNmDemandPdf = getFileNmDemandPdf();
	let xhr = new XMLHttpRequest();
	let pdfRet = false;
	xhr.open("GET",fileNmDemandPdf,true);
	xhr.onload = function (e) {
		if (xhr.readyState === 4) {
			if (xhr.status === 200) {
				let responce = xhr.responseText;
				pdfRet = linkDemandPdf(responce);
			}
		}
		setOutputDemandComment(ret, pdfRet);
	}
	xhr.send(null);
}

/**
 * 需給関連情報PDFリンク
 * PDFファイル、リンク名の取得
 */
function linkDemandPdf(responce){
	let fileNm = "";
	let linkNm = "";

	// PDFファイル、リンク名を取得
	let arrPdf = responce.split(/\n/);
	if (arrPdf) {
		arrPdf.forEach(element => {
			if (element.substring(0,10) == "[filename]") {
				fileNm = element.replace("[filename]", "");
			} else if (element.substring(0,10) == "[linkname]") {
				linkNm = element.replace("[linkname]", "");
			}
		});
		createDispDemandPdf(fileNm, linkNm);
		return true;
	} else {
		// ファイル内部が空白の場合は、非公開とする
		return false;
	}
}

/**
 * 需給関連情報PDFリンク
 * 表示内容の生成
 */
function createDispDemandPdf(fileNm, linkNm){
	let demandCommentPdf = $('#demand_comment_pdf');
	demandCommentPdf.empty();
	let fileNmPath = getFilePlace("/" + fileNm, conDemandCommentDir, "");

	// リンク作成
	let aTag = $("<a></a>");
	aTag.addClass("mb0");
	aTag.addClass("mt0");
	aTag.attr('href', fileNmPath);
	aTag.attr('target', "_blank");
	aTag.attr('style', "opacity: 1;");
	aTag.append(linkNm);
	demandCommentPdf.append(aTag);
}

/**
 * 需給関連情報コメント、PDFリンク
 * 画面出力の設定
 */
function setOutputDemandComment(ret, pdfRet){
	if(ret || pdfRet){
		$('#demand_comment').show();
	} else {
		$('#demand_comment').hide();
	}
}

/**
 * 予備項目用のリンク
 * 最大10ブロックの項目取得
 */
function txtReserveItems(responce){
	// 予備項目配列
	let arrReserveItems = [];

	// PDFファイル名を取得
	let arrPdf = responce.split(/\n/);

	// 予備項目配列作成（最大10ブロック）
	for(i = 0; i < 10; i ++) {
		let title = "";
		let note = "";
		let fileName = "";
		let linkName = "";
		
		arrPdf.forEach(element => {
			// タイトル・説明・PDFファイル名・PDFリンクを取得
			if (element.substring(0,9) == "[" + i + "_title]") {
				title = element.replace("[" + i + "_title]", "");
			}
			if (element.substring(0,8) == "[" + i + "_note]") {
				note = element.replace("[" + i + "_note]", "");
			}
			if (element.substring(0,12) == "[" + i + "_filename]") {
				fileName = element.replace("[" + i + "_filename]", "");
			}
			if (element.substring(0,12) == "[" + i + "_linkname]") {
				linkName = element.replace("[" + i + "_linkname]", "");
			}
		});

		// タイトルが取得できた場合は設定あり
		if (title) {
			arrReserveItems.push({
				"title":title,
				"note":note,
				"fileName":fileName,
				"linkName":linkName
			});
		}
	}
	setOutputReserveItems(arrReserveItems);
}

/**
 * 予備項目用のリンク
 * 画面出力の設定
 */
function setOutputReserveItems(arrReserveItems){
	arrReserveItems.forEach((val, i) => {
		let item = $('#item_' + i);
		let itemTitle = $('#item_' + i + '_title');
		let itemNote = $('#item_' + i + '_note');
		let itemLink = $('#item_' + i + '_link');
		let itemList = $('#item_' + i + '_list');

		itemTitle.empty();
		itemTitle.append(val['title']);
		itemNote.empty();
		itemNote.append(val['note']);
		itemLink.empty();
		itemLink.append(val['linkName']);

		let fileNm = getFilePlace("/" + val['fileName'], conReserveItemsDir, "");
		//href属性の値を書き換える
		itemLink.attr('href', fileNm);

		// リンク項目のサイズ調整
		if (window.matchMedia('(max-width: 768px)').matches) {
			// スマホ
			itemList.css({"height":"39px"});
		} else {
			// PC
			itemList.css({"height":"61px"});
		}
		item.show();
	});

}
