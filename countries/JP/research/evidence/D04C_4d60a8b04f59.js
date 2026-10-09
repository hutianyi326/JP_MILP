$(function() {

	/**
	 * 年度でグループ化された月別データのリンクを生成
	 */
	function createMonthLink(data, $wrapper) {
		if (!data.length) {
			$wrapper.remove();
			return;
		}

		const contents = [];
		const $list = $('<div class="l-row l-row-gutter--10px l-row-gutter-sp--20px u-mt-15"></div>');
		let $instance = null;
		let currentYear = 0;
		data.forEach(e => {
			if (e.year !== currentYear) {
				if ($instance) {
					contents.push($instance);
				}
				currentYear = e.year;
				contents.push('<p class="c-text u-mt-15">' + currentYear + '年</p>');
				$instance = $list.clone();
			}
			$item = `
			<div class="l-col-4 l-col-6-sp">
				<div class="p-link">
					<ul class="p-link__list">
						${getLinkItem(e)}
					</ul>
				</div>
			</div>
			`;
			$instance.append($item);
		});
		contents.push($instance);
		$wrapper.append(contents);
	}

	/**
	 * 年度別データのリンクを生成
	 */
	function createYearLink(data, $wrapper, removeLatest = false) {
		if (!data.length) {
			$wrapper.remove();
			return;
		}

		const contents = [];
		const $list = $('<div class="l-row l-row-gutter--10px l-row-gutter-sp--20px u-mt-15"></div>');
		data.forEach((e, index) => {
			if (!removeLatest || index) {
				$item = `
				<div class="l-col-4 l-col-6-sp">
					<div class="p-link">
						<ul class="p-link__list">
							${getLinkItem(e)}
						</ul>
					</div>
				</div>`;
				contents.push($item);
			}
		});
		$list.append(contents);
		$wrapper.append($list);
	}

	/**
	 * 単純なリンク生成
	 */
	function createLink(data, $wrapper) {
		if (!data.length) {
			$wrapper.remove();
			return;
		}

		const contents = [];
		data.forEach(e => {
			contents.push(getLinkItem(e));
		});
		$wrapper.append(contents);
	}

	/**
	 * データからリンクのhtmlを取得
	 */
	function getLinkItem (e) {
		const label = e.month ? `${e.year}年${e.month}月` : `${e.year}年度`;
		return `<li class="p-link__item"><a href="${e.path}" class="p-link__link c-link" target="_blank"><span>${label}</span><span class="c-link--type01">[${e.ext}：${e.size}KB]</span></a></li>`;
	}

	/**
	 * ユニット別発電実績のリンクを生成
	 */
	function createResultByUnitLink(data, $wrapper, rename = false) {
		if (!data.length) {
			$wrapper.remove();
			return;
		}

		const contents = [];
		const $list = $('<div class="l-row l-row-gutter--10px l-row-gutter-sp--20px u-mt-15"></div>');
		data.forEach((e, index) => {
			const label = (rename && e.filename.match(/^(hatsudenzip_\d{8}\.zip|bghatsu_04_\d{8}\.csv)$/)) ? `${e.ext}ダウンロード` : e.filename;
			$item = `
			<div class="l-col-4 l-col-6-sp">
				<div class="p-link">
					<ul class="p-link__list">
						<li class="p-link__item"><a href="${e.path}" class="p-link__link c-link" target="_blank"><span>${label}</span><span class="c-link--type01">[${e.size}KB]</span></a></li>
					</ul>
				</div>
			</div>`;
			contents.push($item);
		});
		$list.append(contents);
		$wrapper.append($list);
	}

	/**
	 * 最新年のファイルをリンク先としてセット
	 */
	function setLatestLink(data, $link) {
		if (!data.length) {
			$link.remove();
			return;
		}

		$link.attr('href', data[0].path);
	}

	/**
	 * エリアの電力使用状況、系統の需給に関する情報の30分ごとのCSVのリンクにファイルサイズ表記を追加
	 */
	function setRecentGridSupplyDemand(data) {
		const $links = $('.js-csvlink');
		$links.each((index, element) => {
			const hrefFile = $(element).attr('href').split('/').pop();
			const file = data.find(e => e.path.indexOf(hrefFile) !== -1);
			if (file.size) {
				$(element).append('<span class="c-link--type01">[' + file.ext + '：' + file.size + 'KB]</span>');
			}
		});
	}

	$.ajax({
		type: 'GET',
		url: '/denkiyoho/resource/php/getFilesInfo.php',
		success: function(data){
			setRecentGridSupplyDemand(data);
			// 電力使用状況データ月別
			const collection1 = data.filter(e => e.category == '月別電力使用状況').sort((a,b) => b.year - a.year);
			createMonthLink(collection1, $('#month_performance_link'));
			// 系統の需給に関する情報月別
			const collection2 = data.filter(e => e.category == '系統の需給に関する情報').sort((a,b) => b.filename > a.filename ? 1 : -1);
			createMonthLink(collection2, $('#month_grid_supply_demand_Link'));
			// エリア需要実績データ直近
			const collection3 = data.filter(e => e.category == '直近のエリア需要実績').sort((a,b) => b.filename > a.filename ? 1 : -1);
			createLink(collection3, $('#current_demand_link'));
			// エリア需給実績データ年度別
			const collection4 = data.filter(e => e.category == '年別エリア需給実績').sort((a,b) => (a.ext === 'ZIP') ? -1 : b.year - a.year);
			createYearLink(collection4, $('#year_performance_link'));
			// 再生可能エネルギー出力制御指示内容
			const collection5 = data.filter(e => e.category == '再エネ出力制御指示内容').sort((a,b) => b.year - a.year);
			createYearLink(collection5, $('#renewable_energy_content_link'), true);
			setLatestLink(collection5, $('#renewableEnergyCurrentTermContentPDF'));
			// 再生可能エネルギー出力制御指示回数
			const collection6 = data.filter(e => e.category == '再エネ出力制御指示回数').sort((a,b) => b.year - a.year);
			createYearLink(collection6, $('#renewable_energy_count_link'), true);
			setLatestLink(collection6, $('#renewableEnergyCurrentTermCountPDF'));
			// ユニット別発電実績
			const collection7 = data.filter(e => e.category == 'ユニット別発電実績公開用').sort((a,b) => b.order - a.order);
			createResultByUnitLink(collection7, $('#hatsuden_link_general'), true);
			const collection8 = data.filter(e => e.category == 'ユニット別発電実績非公開用').sort((a,b) => b.order - a.order);
			createResultByUnitLink(collection8, $('#hatsuden_link_renkei'), false);
		},
		error: function (request, status, error) {
			console.error(request, status, error);
		}
	})
});
