var denkiYoho = {};
denkiYoho.flag = {
	updateTime: 0,
	updateTimeHour: 0,
	updateTimeMin: 0,
	currentTime: 0
};
denkiYoho.getCsvEndpoint = '/denkiyoho/resource/php/getCsv.php';
denkiYoho.now = new Date();
// 年度の境目を3月31日17時に設定する
denkiYoho.termBoundary = 33117;
denkiYoho.currentTerm = (function () {
	var mdh;
	var currentTerm = denkiYoho.now.getFullYear();
	mdh = (denkiYoho.now.getMonth() + 1) * 10000;
	mdh += denkiYoho.now.getDate() * 100;
	mdh += denkiYoho.now.getHours();
	if (mdh < denkiYoho.termBoundary) currentTerm--;
	return currentTerm;
}());

/* ---------------------------------------------------------------
 * add color class to first argument according to the second argument
--------------------------------------------------------------- */

denkiYoho.addColor = function(element, rate) {
	var colorClass;
	if (rate === '') {
		colorClass = 'c-icon--glay';
	} else if (rate < 92) {
		colorClass = 'c-icon--green';
	} else if (rate < 97) {
		colorClass = 'c-icon--yellow';
	} else {
		colorClass = 'c-icon--red';
	}
	if (colorClass) $(element).addClass(colorClass);
};

denkiYoho.createElements = function(block, time, useRate, reserveRate){
	let mergeText;
	if (block === 'crossRegion') {
		mergeText = (
			'<div class="time01">' +
			denkiYoho.format.time3(time, false) +
			'</div><div class="percent_box-inr two-column"><div class="percent01"><span>' +
			denkiYoho.format.text(useRate, '---') +
			'<span class="min">&#37;</span></span></div>'
		);
		if (reserveRate !== false) {
			mergeText += (
				'<div class="percent02"><span class="percent02--min">広域ブロック予備率</span>' +
				denkiYoho.format.text(reserveRate, '---') +
				'<span class="min">&#37;</span></div>'
			);
		}
		mergeText += '</div>';
	}
	return mergeText;
};

/* ---------------------------------------------------------------
 * きょうのエリアの電力使用状況グラフ
--------------------------------------------------------------- */

denkiYoho.drawGraph = function() {
	var graphData = {
		todayData: [],
		forecastData: [],
		yesterWeekData: [],
		yesterDayData: [],
		realtimeData: [],
		sunData: [],
		sunData2: []
	},
	xAxisMin = 0,
	xAxisMax = 240,
	xAxisSpan = 10,
	yAxisMin = 0,
	yAxisMax = 2900,
	yAxisSpan = 500,
	topLine = [ [xAxisMin, yAxisMax], [xAxisMax, yAxisMax] ],
	btmLine = [ [xAxisMin, yAxisMin], [xAxisMax, yAxisMin] ],
	peakTime, i, graphOption,
	sampleNumber = (60 * 24) / 5, // データ5分刻みの場合。1日を5分刻みにするとサンプル数の最多は288となる。6分値の場合は240になります。
	allGraphData,
	graphColors = [
		'#3c3',    // 当日実績（1時間値）
		'#f93',    // 予想値
		'#03c',    // 前週同様日実績
		'#6cf',    // 前日実績
		'#c6c',    // 予想最大電力
		'#f33',    // 電力ピーク時供給力
		'#ff9494', // 使用率ピーク時供給力
		'#3c3',    // 当日実績（瞬時値）
		'#fc5956'  // 太陽光発電実績
	],
	xAxisTicks = [],
	yAxisTicks = [];
	const graphContent = $('.graph_content');

	denkiYoho.flag.currentTime = -1; // 0の時点のケース、0のデータすら存在しない可能性があるため、-1で初期化する必要がある
	for (i = 0; i < 24; i++) {
		xAxisTicks.push([i * xAxisSpan, i + '']);

		// data: todayData
		graphData.todayData.push([i * xAxisSpan, (denkiYoho.getData.graph.lineData.today[i] - 0)]);
		if (denkiYoho.getData.graph.lineData.today[i]) denkiYoho.flag.currentTime = i; // 存在する当日値の末端を記録している

		// data: forecastData
		graphData.forecastData.push([i * xAxisSpan, (denkiYoho.getData.graph.lineData.forecast[i] - 0)]);

		// data: yesterWeekData
		graphData.yesterWeekData.push([(i * xAxisSpan) + 5, parseInt(denkiYoho.getData.graph.lineData.yesterWeek[i])]);

		// data: yesterDayData
		graphData.yesterDayData.push([(i * xAxisSpan) + 5, parseInt(denkiYoho.getData.graph.lineData.yesterDay[i])]);
	}
	xAxisTicks.push([xAxisTicks.length * xAxisSpan, '']);
	for (i = 0; i < 7; i++) yAxisTicks.push([i * yAxisSpan, denkiYoho.format.num(i * yAxisSpan)]);

	for (i = 0; i < sampleNumber; i++) {
		// data: realtimeData
		// 6分値の場合の処理。iをそのままxとして指定して問題ない。
		// graphData.realtimeData.push([i, parseInt(denkiYoho.getData.graph.lineData.realtime[i])]);
		// 5分値の場合の処理。グラフのxが0~230になっており5分値のサンプル数は288なので、0~230を0~288にスケール変換した結果のxを計算する必要がある。
		graphData.realtimeData.push([i*0.835, parseInt(denkiYoho.getData.graph.lineData.realtime[i])]);

		// data: sunData
		// 6分値の場合の処理。iをそのままxとして指定して問題ない。
		// graphData.sunData.push([i, parseInt(denkiYoho.getData.graph.lineData.sun[i])]);
		// 5分値の場合の処理。グラフのxが0~230になっており5分値のサンプル数は288なので、0~230を0~288にスケール変換した結果のxを計算する必要がある。
		graphData.sunData.push([i*0.835, parseInt(denkiYoho.getData.graph.lineData.sun[i])]);

		// data: sunData2
		// 6分値の場合の処理。iをそのままxとして指定して問題ない。
		// graphData.sunData2.push([i, parseInt(denkiYoho.getData.graph.lineData.sun[i])]);
		// 5分値の場合の処理。グラフのxが0~230になっており5分値のサンプル数は288なので、0~230を0~288にスケール変換した結果のxを計算する必要がある。
		graphData.sunData2.push([i*0.835, parseInt(denkiYoho.getData.graph.lineData.sun2[i])]);
	}

	// data: peakSupply
	peakTime = denkiYoho.format.time2(denkiYoho.getData.graph.data.peakSupplyTime, 'array');
	graphData.peakSupply = [
		[peakTime[0] * xAxisSpan, parseInt(denkiYoho.getData.graph.data.peakSupply)],
		[peakTime[1] * xAxisSpan, parseInt(denkiYoho.getData.graph.data.peakSupply)]
	];

	// data: peakForecast
	peakTime = denkiYoho.format.time2(denkiYoho.getData.graph.data.peakForecastTime, 'array');
	graphData.peakForecast = [
		[peakTime[0] * xAxisSpan, parseInt(denkiYoho.getData.graph.data.peakForecastSupply)],
		[peakTime[1] * xAxisSpan, parseInt(denkiYoho.getData.graph.data.peakForecastSupply)]
	];

	// data: peakUseRateSupply
	peakTime = denkiYoho.format.time2(denkiYoho.getData.graph.data.peakUseRateSupplyTime, 'array');
	graphData.peakUseRateSupply = [
		[peakTime[0] * xAxisSpan, parseInt(denkiYoho.getData.graph.data.peakUseRateSupply)],
		[peakTime[1] * xAxisSpan, parseInt(denkiYoho.getData.graph.data.peakUseRateSupply)]
	];

	allGraphData = [
		{
			data: graphData.todayData,
			bars: { show: true }
		}, {
			data: graphData.forecastData,
			bars: { show: true }
		}, {
			data: graphData.yesterWeekData,
			lines: { show: true }
		}, {
			data: graphData.yesterDayData,
			lines: { show: true }
		}, {
			data: graphData.peakForecast,
			lines: { show: true },
			points: { show: true }
		}, {
			data: graphData.peakSupply,
			lines: { show: true },
			points: { show: true }
		}, {
			data: graphData.peakUseRateSupply,
			lines: { show: true },
			points: { show: true }
		}, {
			data: graphData.realtimeData,
			lines: { show: true }
		}, {
			data: graphData.sunData,
			lines: { show: true }
		}, {
			data: topLine,
			lines: { show: false }
		}, {
			data: btmLine,
			lines: { show: false }
		}
	];
	graphOption = {
		colors: graphColors,
		xaxis: {
			ticks: xAxisTicks
		},
		yaxis: {
			ticks: yAxisTicks
		}
	};

	function plotGraph(graphID) {
		switch (graphID) {
			case '#graph_all':
				// PLOT graphAll
				allGraphData[2].lines.show = true;
				allGraphData[3].lines.show = true;
				break;
			case '#graph_none':
				// PLOT graphNone
				allGraphData[2].lines.show = false;
				allGraphData[3].lines.show = false;
				break;
		}
		$.plot($(graphID), allGraphData, graphOption);
	}

	$.each([
		'#graph_all',
		'#graph_none',
	], function(index, value) {
		plotGraph(value);
	});

	// default display graph
	graphContent.eq(1).show();
	graphContent.eq(0).hide();
};

/* ---------------------------------------------------------------
 * きょう、あす、あさっての電力需給見通し
--------------------------------------------------------------- */
denkiYoho.insertData = function() {
	// #date: 2013年00月00日の電力需給状況
	const dateText = denkiYoho.format.date(denkiYoho.getData.date, 3, false);
	$(denkiYoho.setDoms.date1).text(dateText + 'の電力需給状況');
	$(denkiYoho.setDoms.date3).text(dateText + 'の電力需給状況');

	// データプロット
	function setProspectIndicator(target) {
		const data = denkiYoho.getData[target];

		// 広域ブロック情報
		const wideArea = {
			demand: $(denkiYoho.setDoms[target].wideAreaInfo01),
			use: $(denkiYoho.setDoms[target].wideAreaInfo02),
		}
		if (wideArea.demand.length) {

			// きょうの広域ブロック需要ピーク時前半の使用率・予備率
			$(wideArea.demand[0]).html(
				denkiYoho.createElements(
					'crossRegion',
					data.demandFirstTime,
					data.demandFirstUse,
					data.demandFirstReserve
				)
			);
			denkiYoho.addColor($(wideArea.demand[0]).find('.percent01>span').eq(0), data.demandFirstUse);

			// きょうの広域ブロック需要ピーク時後半の使用率・予備率
			$(wideArea.demand[1]).html(
				denkiYoho.createElements(
					'crossRegion',
					data.demandSecondTime,
					data.demandSecondUse,
					data.demandSecondReserve
				)
			);
			denkiYoho.addColor($(wideArea.demand[1]).find('.percent01>span').eq(0), data.demandSecondUse);


			// きょうの広域ブロック使用率ピーク時前半の使用率
			$(wideArea.use[0]).html(
				denkiYoho.createElements(
					'crossRegion',
					data.useRateFirstTime,
					data.useRateFirstUse,
					data.useRateFirstReserve
				)
			);
			denkiYoho.addColor($(wideArea.use[0]).find('.percent01>span').eq(0), data.useRateFirstUse);

			// きょうの広域ブロック使用率ピーク時後半の使用率
			$(wideArea.use[1]).html(
				denkiYoho.createElements(
					'crossRegion',
					data.useRateSecondTime,
					data.useRateSecondUse,
					data.useRateSecondReserve
				)
			);
			denkiYoho.addColor($(wideArea.use[1]).find('.percent01>span').eq(0), data.useRateSecondUse);
		}

		const content = {};

		// 更新日時
		const updateDate = denkiYoho.format.date(denkiYoho.getData.date, 3, false);
		const updateTime = denkiYoho.format.time(data.updateTime);
		if (updateDate && updateTime) {
			content.updateDate = `（${updateDate}${updateTime}更新）`;
		}

		// エリア情報
		if (target === 'tomorrow' && !data?.peakSupply) {
			// あすのデータはpeakSupplyがなければエリア情報をプロットしない
			$('#' + target).addClass('data_none');
		} else {
			const setDataOrBlank = e => (data[e] ? denkiYoho.format.num(data[e]) : '-----') + '<span class="meter01--min">万kW</span>';
			const unitText = '<span class="min">&#37;</span>';
			Object.assign(content,
				{
					use: denkiYoho.format.text(data.use, '-----') + unitText,
					reserve: denkiYoho.format.text(data.reserve, '-----') + unitText,
					peakForecastTime: denkiYoho.format.time3(data.peakForecastTime, false),
					use02: denkiYoho.format.text(data.use02, '-----') + unitText,
					reserve02: denkiYoho.format.text(data.reserve02, '-----') + unitText,
					peakForecastTime02: denkiYoho.format.time3(data.peakForecastTime02, false),
					peakForecast: setDataOrBlank('peakForecast'),
					peakForecast02: setDataOrBlank('peakForecast02'),
					minPeakForecast: setDataOrBlank('minPeakForecast'),
					peakSupply: setDataOrBlank('peakSupply'),
					peakSupply02: setDataOrBlank('peakSupply02'),
				}
			);
		}
		for (key in content) {
			$(denkiYoho.setDoms[target][key]).html(content[key])
		}
	}
	setProspectIndicator('today');
	setProspectIndicator('tomorrow');
	setProspectIndicator('twoDaysLater');

	// #graph
	function graphBlock() {
		var elements, graphReference, graphReferencePercent, mergeText;
		denkiYoho.getData.graph.text.hourSupply = denkiYoho.getData.graph.lineData.today[parseInt(denkiYoho.flag.currentTime)];
		denkiYoho.getData.graph.text.foreSupply = denkiYoho.getData.graph.lineData.forecast[denkiYoho.flag.updateTimeHour];

		elements = $(denkiYoho.setDoms.graph.crossRegionText.contentArea).find('.percent_box');

		if (elements.length) {
			$(elements[0]).html(
				denkiYoho.createElements(
					'crossRegion',
					denkiYoho.getData.graph.text.crossRegionFirstTime,
					denkiYoho.getData.graph.text.crossRegionFirstUseRate,
					false
				)
			);
			denkiYoho.addColor($(elements[0]).find('.percent01>span').eq(0), denkiYoho.getData.graph.text.crossRegionFirstUseRate);
			$(elements[1]).html(
				denkiYoho.createElements(
					'crossRegion',
					denkiYoho.getData.graph.text.crossRegionSecondTime,
					denkiYoho.getData.graph.text.crossRegionSecondUseRate,
					false
				)
			);
			denkiYoho.addColor($(elements[1]).find('.percent01>span').eq(0), denkiYoho.getData.graph.text.crossRegionSecondUseRate);
		}

		// #graph-hourUse: 00%
		mergeText = denkiYoho.getData.graph.text.hourUse ? denkiYoho.getData.graph.text.hourUse : '---';
		$(denkiYoho.setDoms.graph.text.hourUse).html(mergeText + '<span class="min">&#37;</span>');

		// #graph-hourSupply: 0,000万kW
		mergeText = denkiYoho.getData.graph.text.hourSupply
			? denkiYoho.format.num(denkiYoho.getData.graph.text.hourSupply)
			: '---';
		$(denkiYoho.setDoms.graph.text.hourSupply).html(mergeText + '<span class="meter01--min">万kW</span>');

		// #graph-nowUse: 00%
		mergeText = denkiYoho.getData.graph.text.nowUse ? denkiYoho.getData.graph.text.nowUse : '---';
		$(denkiYoho.setDoms.graph.text.nowUse).html(mergeText + '<span class="min">&#37;</span>');

		// #graph-nowSupply: 0,000万kW
		mergeText = denkiYoho.getData.graph.text.nowSupply
			? denkiYoho.format.num(denkiYoho.getData.graph.text.nowSupply)
			: '---';
		$(denkiYoho.setDoms.graph.text.nowSupply).html(mergeText + '<span class="meter01--min">万kW</span>');

		// #graph-foreUse: 00%
		mergeText = denkiYoho.getData.graph.text.foreUse ? denkiYoho.getData.graph.text.foreUse : '---';
		$(denkiYoho.setDoms.graph.text.foreUse).html(mergeText + '<span class="min">&#37;</span>');

		// #graph-foreSupply: 0,000万kW
		mergeText = denkiYoho.getData.graph.text.foreSupply
			? denkiYoho.format.num(denkiYoho.getData.graph.text.foreSupply)
			: '---';
		$(denkiYoho.setDoms.graph.text.foreSupply).html(mergeText + '<span class="meter01--min">万kW</span>');

		// 0時の場合にundefinedになるため、「---」とする
		if (typeof denkiYoho.getData.graph.text.reference === 'undefined' || denkiYoho.getData.graph.text.reference === '') {
			$(denkiYoho.setDoms.graph.text.reference).html('---<span class="min">万kW</span>');
			$(denkiYoho.setDoms.graph.text.referencePercent).html('---%');
		} else {
			// #graph-reference: 0,000万kW
			graphReference = denkiYoho.format.num(denkiYoho.getData.graph.text.reference);
			// #graph-referencePercent: 00%
			graphReferencePercent = denkiYoho.format.num(denkiYoho.getData.graph.text.referencePercent);

			$(denkiYoho.setDoms.graph.text.reference).html(graphReference + '<span class="min">万kW</span>');
			$(denkiYoho.setDoms.graph.text.referencePercent).html(graphReferencePercent + '%');
		}

	}
	graphBlock();
};


/* ---------------------------------------------------------------
 * きょうのエリア需要実績状況グラフ
--------------------------------------------------------------- */

denkiYoho.drawDemandGraph = function() {
	var setColumnData = c => denkiYoho.demandData.map( (item, index) => [index * 5, item[c] == '' ? null : (item[c] > 0 ? item[c] / 10 : 0)] );
	var graphData = {
		nuclear: setColumnData(3),
		geothermal: setColumnData(10),
		hydroelectric: setColumnData(9),
		thermal_lng: setColumnData(4),
		thermal_coal: setColumnData(5),
		thermal_oil: setColumnData(6),
		thermal_etc: setColumnData(7),
		biomass: setColumnData(11),
		wind: setColumnData(15),
		solar: setColumnData(13),
		pumped: setColumnData(17),
		battery: setColumnData(18),
		interconnection: setColumnData(19),
		etc: setColumnData(20),
		demand: setColumnData(2)
	},
	xAxisSpan = 10,
	yAxisSpan = 500,
	i, graphOption,
	allGraphData,
	graphColors = [
		'#7030a0',    // 原子力
		'#a00000',    // 地熱
		'#0070c0',    // 水力
		'#ff8080',    // 火力(LNG)
		'#dbdbdb',    // 火力(石炭)
		'#fff2cc',    // 火力(石油)
		'#698ed0',    // 火力(その他)
		'#92d050',    // バイオマス
		'#00b050',    // 風力
		'#ffff00',    // 太陽光
		'#00b0f0',    // 揚水
		'#f1975a',    // 蓄電池
		'#7f7f7f',    // 連系線
		'#c86480',    // その他
		'#ff0000'     // エリア需要
	],
	xAxisTicks = [],
	yAxisTicks = [];
	// console.log(graphData);

	for (i = 0; i < 24; i++) {
		xAxisTicks.push([i * xAxisSpan, i + '']);
	}
	xAxisTicks.push([xAxisTicks.length * xAxisSpan, '']);
	for (i = 0; i < 7; i++) {
		yAxisTicks.push([i * yAxisSpan, denkiYoho.format.num(i * yAxisSpan)]);
	}

	allGraphData = [
		{ data: graphData.nuclear, lines: {show: true, fill: true, fillColor: graphColors[0]}},
		{ data: graphData.geothermal, lines: {show: true, fill: true, fillColor: graphColors[1]} },
		{ data: graphData.hydroelectric, lines: {show: true, fill: true, fillColor: graphColors[2]} },
		{ data: graphData.thermal_lng, lines: {show: true, fill: true, fillColor: graphColors[3]} },
		{ data: graphData.thermal_coal, lines: {show: true, fill: true, fillColor: graphColors[4]} },
		{ data: graphData.thermal_oil, lines: {show: true, fill: true, fillColor: graphColors[5]} },
		{ data: graphData.thermal_etc, lines: {show: true, fill: true, fillColor: graphColors[6]} },
		{ data: graphData.biomass, lines: {show: true, fill: true, fillColor: graphColors[7]} },
		{ data: graphData.wind, lines: {show: true, fill: true, fillColor: graphColors[8]} },
		{ data: graphData.solar, lines: {show: true, fill: true, fillColor: graphColors[9]} },
		{ data: graphData.pumped, lines: {show: true, fill: true, fillColor: graphColors[10]} },
		{ data: graphData.battery, lines: {show: true, fill: true, fillColor: graphColors[11]} },
		{ data: graphData.interconnection, lines: {show: true, fill: true, fillColor: graphColors[12]} },
		{ data: graphData.etc, lines: {show: true, fill: true, fillColor: graphColors[13]} },
		{ data: graphData.demand, lines: {show: true, fill: false, lineWidth: 2}, stack: false, }
	];
	graphOption = {
		series: {
			stack: true,
			lines: {
					show: false,
					fill: true,
					lineWidth: 0,
			}
		},
		colors: graphColors,
		xaxis: {
			ticks: xAxisTicks
		},
		yaxis: {
			ticks: yAxisTicks
		}
	};

	$.plot($('#graph_area_jisseki'), allGraphData, graphOption);
};

/* ---------------------------------------------------------------
 * 電力需給見通し/エリアの電力使用状況 CSVのロード
--------------------------------------------------------------- */

denkiYoho.loadCSV = function() {
	var sampleNumber = (60 * 24) / 5; // データ5分刻みの場合。1日を5分刻みにするとサンプル数の最多は288となる。6分値の場合は240になります。
	var i;
	$.ajax({
		type: 'GET',
		url: denkiYoho.getCsvEndpoint,
		data: {"file": "juyo_cepco003_utf8.csv"},
		success: function(data){
			var csv = $.csv()(data);
			var hourlyDataStartRow = 6;
			var graphDataStartRow = hourlyDataStartRow + 24;
			var offsetRow;

			// 2201以降のフォーマット
			// 1行目 データ更新時刻
			// 2行目 広域ブロックの当日のピーク時の予測
			// 3行目 広域ブロックの翌日のピーク時の予測
			// 4行目 エリアの当日のピーク時の予測
			// 5行目 エリアの翌日のピーク時の予測
			// 6行目 現在のデータ
			// 7~30行目 1時間刻みのデータ
			// 31~318行目 5分刻みのデータ
			// 319行目 あさっての広域ブロック情報

			// GET DATA
			denkiYoho.getData = {
				date: csv[0][0],
				today: {
					demandFirstTime: csv[1][0],
					demandFirstReserve: csv[1][1],
					demandFirstUse: csv[1][2],
					demandSecondTime: csv[1][3],
					demandSecondReserve: csv[1][4],
					demandSecondUse: csv[1][5],
					useRateFirstTime: csv[1][6],
					useRateFirstReserve: csv[1][7],
					useRateFirstUse: csv[1][8],
					useRateSecondTime: csv[1][9],
					useRateSecondReserve: csv[1][10],
					useRateSecondUse: csv[1][11],
					peakSupply: csv[3][0],
					peakForecastTime: csv[3][1],
					updateDate: csv[3][2],
					updateTime: csv[3][3],
					peakForecast: csv[3][4],
					minPeakForecast: csv[3][8],
					reserve: csv[3][12],
					use: csv[3][13],
					peakSupply02: csv[3][14],
					peakForecast02: csv[3][18],
					peakForecastTime02: csv[3][19],
					reserve02: csv[3][22],
					use02: csv[3][23],
				},
				tomorrow: {
					demandFirstTime: csv[2][0],
					demandFirstReserve: csv[2][1],
					demandFirstUse: csv[2][2],
					demandSecondTime: csv[2][3],
					demandSecondReserve: csv[2][4],
					demandSecondUse: csv[2][5],
					useRateFirstTime: csv[2][6],
					useRateFirstReserve: csv[2][7],
					useRateFirstUse: csv[2][8],
					useRateSecondTime: csv[2][9],
					useRateSecondReserve: csv[2][10],
					useRateSecondUse: csv[2][11],
					peakSupply: csv[4][0],
					peakForecastTime: csv[4][1],
					updateDate: csv[4][2],
					updateTime: csv[4][3],
					peakForecast: csv[4][4],
					minPeakForecast: csv[4][8],
					reserve: csv[4][12],
					use: csv[4][13],
					peakSupply02: csv[4][14],
					peakForecast02: csv[4][18],
					peakForecastTime02: csv[4][19],
					reserve02: csv[4][22],
					use02: csv[4][23],
				},
				twoDaysLater: {
					demandFirstTime: csv[318][0],
					demandFirstReserve: csv[318][1],
					demandFirstUse: csv[318][2],
					demandSecondTime: csv[318][3],
					demandSecondReserve: csv[318][4],
					demandSecondUse: csv[318][5],
					useRateFirstTime: csv[318][6],
					useRateFirstReserve: csv[318][7],
					useRateFirstUse: csv[318][8],
					useRateSecondTime: csv[318][9],
					useRateSecondReserve: csv[318][10],
					useRateSecondUse: csv[318][11],
					updateTime: csv[318][13],
				},
				graph: {
					// LEFT
					data: {
						peakSupplyTime: csv[3][1],
						peakSupply: csv[3][0],
						peakForecastTime: csv[3][5],
						peakForecastSupply: csv[3][4],
						// 使用率ピーク時供給力
						peakUseRateSupplyTime: csv[3][15],
						peakUseRateSupply: csv[3][14]
					},
					// RIGHT
					text: {
						crossRegionFirstTime: csv[5][0],
						crossRegionFirstUseRate: csv[5][1],
						crossRegionSecondTime: csv[5][2],
						crossRegionSecondUseRate: csv[5][3],
						hourUse: csv[5][4],
						hourSupply: '',
						nowUse: csv[5][5],
						nowSupply: '',
						foreUse: csv[5][6],
						foreSupply: '',
						reference: 0,
						referencePercent: 0
					}
				}
			};

			denkiYoho.getData.graph.lineData = {
				today: [],
				forecast: [],
				yesterWeek: [],
				yesterDay: [],
				realtime: [],
				sun: [],
				sun2: []
			};

			for (i = 0; i < 24; i++) {
				offsetRow = i + hourlyDataStartRow;

				// lineData - day
				denkiYoho.getData.graph.lineData.today[i] = csv[offsetRow][2]; // 当日実績
				denkiYoho.getData.graph.lineData.forecast[i] = csv[offsetRow][3]; // 当日予測
				denkiYoho.getData.graph.lineData.yesterDay[i] = csv[offsetRow][4]; // 前日実績
				denkiYoho.getData.graph.lineData.yesterWeek[i] = csv[offsetRow][5]; // 前週同曜日実績
			}

			// graphLineData - realtime and sun
			for (i = 0; i < sampleNumber; i++) {
				offsetRow = i + graphDataStartRow;

				denkiYoho.getData.graph.lineData.realtime[i] = csv[offsetRow][2];
				denkiYoho.getData.graph.lineData.sun[i] = csv[offsetRow][3];
				denkiYoho.getData.graph.lineData.sun2[i] = csv[offsetRow][4];

				// reference
				if (csv[offsetRow][2]) {
					denkiYoho.getData.graph.text.nowSupply = csv[offsetRow][2];
					denkiYoho.getData.graph.text.reference = csv[offsetRow][3];
					denkiYoho.getData.graph.text.referencePercent = csv[offsetRow][4];
				}
			}
		},
		complete: function() {
			if (typeof denkiYoho.getData === 'undefined') return;
			denkiYoho.getCSVUpdateTime(denkiYoho.getData.date);
			denkiYoho.drawGraph();
			denkiYoho.insertData();
		}
	});
};


/* ---------------------------------------------------------------
 * 再生可能エネルギー出力制御の見通し CSVのロード
--------------------------------------------------------------- */

denkiYoho.loadCSVRenewableEnergy = function() {
	var renewableEnergyUpdateDate = document.getElementById('renewableEnergyUpdateDate');
	var regexp = /(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?/g;

	if (renewableEnergyUpdateDate == null) return;

	$.ajax({
		type: 'GET',
		url: denkiYoho.getCsvEndpoint,
		data: {"file": "saiene_shutsuryoku_seigyo.csv"},
		success: function(data){
			var csv = $.csv()(data);
			var date, cell;
			renewableEnergyUpdateDate.textContent = (
				'（' +
				denkiYoho.format.date(csv[0][0].replace(regexp, '$1/$2/$3'), 3, false) +
				denkiYoho.format.time(csv[0][0].replace(regexp, '$4:$5')) +
				'更新）'
			);
			date = denkiYoho.format.date(csv[1][1].replace(regexp, '$2/$3'), 2, false);
			cell = document.getElementById('renewableEnergyDate1Date');
			cell.textContent = date;
			cell.insertAdjacentHTML('beforeend', '<br>' + csv[1][2]);
			date = denkiYoho.format.date(csv[2][1].replace(regexp, '$2/$3'), 2, false);
			cell = document.getElementById('renewableEnergyDate2Date');
			cell.textContent = date;
			cell.insertAdjacentHTML('beforeend', '<br>' + csv[2][2]);
			date = denkiYoho.format.date(csv[3][1].replace(regexp, '$2/$3'), 2, false);
			cell = document.getElementById('renewableEnergyDate3Date');
			cell.textContent = date;
			cell.insertAdjacentHTML('beforeend', '<br>' + csv[3][2]);
			document.getElementById('renewableEnergyDate1Control').textContent = csv[1][3];
			document.getElementById('renewableEnergyDate2Control').textContent = csv[2][3];
			document.getElementById('renewableEnergyDate3Control').textContent = csv[3][3];
		}
	});
};

/* ---------------------------------------------------------------
 * きょうのエリア需要実績状況 CSVのロード
--------------------------------------------------------------- */

denkiYoho.loadCSVDemandResult = function () {
	const now = new Date();
	$.ajax({
		type: 'GET',
		url: denkiYoho.getCsvEndpoint,
		data: {"file": "eria_jukyu_" + now.getFullYear() + ('0'+(now.getMonth()+1)).slice(-2) + "_04.csv"},
		success: function(data){
			const csv = $.csv()(data);
			const today = now.getDate();
			denkiYoho.demandData = csv.filter(row => new Date(row[0]).getDate() === today);
			const shortage = 49 - denkiYoho.demandData.length;
			for (let i = 1; i <= shortage; i++) {
				// 足りないデータを空行で埋める
				denkiYoho.demandData.push([today, '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '' ]);
			}
		},
		complete: function() {
			if (typeof denkiYoho.demandData === 'undefined') return;
			denkiYoho.drawDemandGraph();
		}
	});
}
/* ---------------------------------------------------------------
 * set DOM
--------------------------------------------------------------- */

denkiYoho.setDoms = {
	date1: '#date1',
	date2: '#date2',
	date3: '#date3',
	today: {
		updateDate: '#today-updateDate',
		use: '#today-use01',
		use02: '#today-use02',
		reserve: '#today-reserve01',
		reserve02: '#today-reserve02',
		peakForecast: '#today-peakForecast',
		peakForecast02: '#today-peakForecast02',
		minPeakForecast: '#today-minPeakForecast',
		peakForecastTime: '.today-peakForecast-time',
		peakForecastTime02: '.today-peakForecast-time02',
		peakSupply: '#today-peakSupply',
		peakSupply02: '#today-peakSupply02',
		wideAreaInfo01: '#gtab-01 .percent_box',
		wideAreaInfo02: '#gtab-03 .percent_box',
	},
	tomorrow: {
		updateDate: '#tomorrow-updateDate',
		use: '#tomorrow-use01',
		use02: '#tomorrow-use02',
		reserve: '#tomorrow-reserve01',
		reserve02: '#tomorrow-reserve02',
		peakForecast: '#tomorrow-peakForecast',
		peakForecast02: '#tomorrow-peakForecast02',
		minPeakForecast: '#tomorrow-minPeakForecast',
		peakForecastTime: '.tomorrow-peakForecast-time',
		peakForecastTime02: '.tomorrow-peakForecast-time02',
		peakSupply: '#tomorrow-peakSupply',
		peakSupply02: '#tomorrow-peakSupply02',
		wideAreaInfo01: '#gtab-08 .percent_box',
		wideAreaInfo02: '#gtab-10 .percent_box',
	},
	twoDaysLater: {
		updateDate: '#twoDaysLater-updateDate',
		wideAreaInfo01: '#gtab-12 .percent_box',
		wideAreaInfo02: '#gtab-13 .percent_box',
	},
	graph: {
		crossRegionText: {
			contentArea: '#graph_rate06'
		},
		text: {
			hourUse: '#graph-hourUse',
			hourSupply: '#graph-hourSupply',
			nowUse: '#graph-nowUse',
			nowSupply: '#graph-nowSupply',
			foreUse: '#graph-foreUse',
			foreSupply: '#graph-foreSupply',
			reference: '#graph-reference',
			referencePercent: '#graph-referencePercent'
		}
	}
};

/* ---------------------------------------------------------------
 * data format
--------------------------------------------------------------- */

denkiYoho.format = {};

/* default text */
denkiYoho.format.text = function(text, noData) {
	return text ? text : noData;
};

/* num */
denkiYoho.format.num = function(defNum) {
	var num = String(defNum).replace(/,/g, '');
	while ((num = num.replace(/^(-?\d+)(\d{3})/, '$1,$2')) !== num);

	return num;
};

/* date */
denkiYoho.format.date = function(defDate, inputFormatType, insertBr) {
	var dateArray, dateTxt;
	if (typeof defDate === 'string' && defDate !== '') {
		dateArray = String(defDate).split('/');

		if (defDate.match('/')) {
			if (inputFormatType === 3) {
				dateTxt = parseInt(dateArray[0]) + '年';
				if (insertBr) dateTxt += '<br>';
				dateTxt += parseInt(dateArray[1]) + '月' + parseInt(dateArray[2]) + '日';
			} else {
				dateTxt = parseInt(dateArray[0]) + '月' + parseInt(dateArray[1]) + '日';
			}
		} else {
			dateTxt = defDate;
		}
	} else {
		dateTxt = false;
	}
	return dateTxt;
};
denkiYoho.format.week = function(defDate) {
	return ['日', '月', '火', '水', '木', '金', '土'][defDate];
};

/* time */
denkiYoho.format.time = function(defTime) {
	var timeArray, timeTxt;
	if (typeof defTime === 'string' && defTime !== '') {
		timeArray = String(defTime).split(':');
		timeTxt = timeArray[0] + '時' + timeArray[1] + '分';
	} else {
		timeTxt = false;
	}
	return timeTxt;
};

/* time2(original format) */
denkiYoho.format.time2 = function(defTime, outputFormatType) {
	var firstTime, lastTime, returnValue, spanArray;
	if (typeof defTime === 'string' && defTime !== '') {
		if (outputFormatType === 'array') {
			spanArray = String(defTime).split(/[〜～]/);
			firstTime = spanArray[0].split(':');
			lastTime = spanArray[1].split(':');
			returnValue = [firstTime[0], lastTime[0]];
		} else {
			returnValue = defTime.replace(/0?(\d+:\d+)/g, '$1');
		}
	} else {
		returnValue = false;
	}
	return returnValue;
};

/* time3 */
denkiYoho.format.time3 = function(defTime, insertBr) {
	var timeArray, timeTxt;
	if (defTime) {
		timeArray = defTime.split(/\D/g);
		timeTxt = Number(timeArray[0]) + '時';
		timeTxt += timeArray[1] + '分';
		timeTxt += '～';
		if (insertBr) timeTxt += '<br>';
		timeTxt += Number(timeArray[2]) + '時';
		timeTxt += timeArray[3] + '分';
	} else {
		timeTxt = '-時--分～';
		if (insertBr) timeTxt += '<br>';
		timeTxt += '-時--分';
	}
	return timeTxt;
};

/* get update time */
denkiYoho.getCSVUpdateTime = function(csvUpdate) {
	var csvUpdateTime;
	if (typeof csvUpdate === 'string' && csvUpdate.indexOf(':') !== -1) {
		csvUpdateTime = (csvUpdate.split(' '))[1];
		denkiYoho.flag.updateTimeHour = parseInt((csvUpdateTime.split(':'))[0]);
		denkiYoho.flag.updateTimeMin = parseInt((csvUpdateTime.split(':'))[1]);
	}
};

/* ---------------------------------------------------------------
 * dom Ready
--------------------------------------------------------------- */

$(document).ready(function() {
	denkiYoho.loadCSV();
	if ($('#renewableEnergyUpdateDate').length) {
		denkiYoho.loadCSVRenewableEnergy();
	}
	if ($('#graph_area_jisseki').length) {
		denkiYoho.loadCSVDemandResult();
	}
});
