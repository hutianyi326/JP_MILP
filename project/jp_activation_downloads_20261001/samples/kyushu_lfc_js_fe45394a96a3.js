// ファイル格納ディレクトリ
const KOUIKI_LFC_CSV_DIR = 'csv/lfc/'
// 広域LFC情報ファイル
const KOUIKI_LFC_INFO_FILE = KOUIKI_LFC_CSV_DIR + 'kouiki_lfc_info_list.csv';
// 広域LFCファイルのプレフィックス
const KOUIKI_LFC_FILE_PREFIX = /^jukyu_LFC_kyushu_/;
// リンクテキスト
const LINK_TEXT_LFC_LASTMONTH = '前月実績の広域LFC情報';
const LINK_TEXT_LFC_MONTHBEFORELAST = '前々月実績の広域LFC情報';

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
 * 年月の取得
 */
function getYM(m){
	const date = new Date();
	date.setMonth(date.getMonth() - m);
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');

	return `${year}${month}`;
}

/**
 * 実施状況の公表リンク作成
 */
function statusDisclosureCreateLink(f, t){
	const match = f.match(/^(.+?)\((.+?)\)$/);
	const href = KOUIKI_LFC_CSV_DIR + match[1] + '?' + currentTime();
	const $a = $('<a>', { href: href });
	const $img = $('<img>', { 'class': 'icon', alt: 'csvファイル', src: '/library/td/images/icon/icon_file.png' });
	const linktext = t + '（' + match[2] + 'KB）';

	return $a.append($img).append(linktext);
}

/**
 * 実施状況の公表
 */
function setStatusDisclosure() {
	$('#lfc_lastMonth').empty();
	$('#lfc_lastMonth').hide();
	$('#lfc_lastMonth_wait').show();
	$('#lfc_monthBeforeLast').empty();
	$('#lfc_monthBeforeLast').hide();
	$('#lfc_monthBeforeLast_wait').show();

	const file = KOUIKI_LFC_INFO_FILE + '?' + currentTime();
	const ym_lastMonth = getYM(1);
	const ym_monthBeforeLast = getYM(2);

	let xhr = new XMLHttpRequest();
	xhr.open("GET", file, true);
	xhr.onload = function (e) {
		if (xhr.readyState === 4) {
			if (xhr.status === 200) {
				let responce = xhr.responseText;
				const rows = responce.trim().split('\n');
				rows.some((line, rowIndex) => {
					const cols = line.split(',');
					return cols.some((col, colIndex) => {
						if (colIndex === 0) return false; // 先頭列の場合はスキップ
						if (col === '-') return false; // 値が「-」の場合はスキップ
						const replaced = col.replace(KOUIKI_LFC_FILE_PREFIX, ''); // プレフィックスを削除
						if (replaced.startsWith(ym_lastMonth)) { // 前月の場合
							$('#lfc_lastMonth').append(statusDisclosureCreateLink(col, LINK_TEXT_LFC_LASTMONTH));
							$('#lfc_lastMonth').show();
							$('#lfc_lastMonth_wait').hide();
							return false; // 前月の設定が終わった場合はスキップ
						}
						if (replaced.startsWith(ym_monthBeforeLast)) { // 前々月の場合
							$('#lfc_monthBeforeLast').append(statusDisclosureCreateLink(col, LINK_TEXT_LFC_MONTHBEFORELAST));
							$('#lfc_monthBeforeLast').show();
							$('#lfc_monthBeforeLast_wait').hide();
							return true; // 前々月の設定が終わった時点で終了
						}
					});
				});
			}
		}
	};
	xhr.send(null);
}

/**
 * 過去のデータダウンロードリンク作成
 */
function downloadHistoricalDataCreateLink(f, t){
	const match = f.match(/^(.+?)\((.+?)\)$/);
	const href = KOUIKI_LFC_CSV_DIR + match[1] + '?' + currentTime();
	const $div = $('<div>', { 'class': 'n_button_area n_block padding-left20 download' });
	const $a = $('<a>', { 'class': 'n_text_link_button', href: href });
	const $img = $('<img>', { 'class': 'icon', alt: 'csvファイル', src: '/library/td/images/icon/icon_file.png' });
	const linktext = t + '<br>（' + match[2] + 'KB）';

	return $div.append($a.append($img).append(linktext));
}

/**
 * 過去のデータダウンロード
 */
function setDownloadHistoricalData() {
	$('#download_historical_data').empty();
	$('#download_historical_data').hide();

	const file = KOUIKI_LFC_INFO_FILE + '?' + currentTime();
	const ym = getYM(2);
	const y = ym.slice(0, 4);
	const m = ym.slice(4);

	let xhr = new XMLHttpRequest();
	xhr.open("GET", file, true);
	xhr.onload = function (e) {
		if (xhr.readyState === 4) {
			if (xhr.status === 200) {
				let responce = xhr.responseText;
				const rows = responce.trim().split('\n');
				rows.forEach((line, rowIndex) => {
					let flag = false;
					$divY = $('<div>', { 'class': 'pbAreaWrapper1' });
					$divM = $('<div>', { 'class': 'pbAreaWrapper1' });
					const cols = line.split(',');
					cols.forEach((col, colIndex) => {
						if (colIndex === 0) { // 先頭列の場合
							if (col > y) return; // 前々月の年より上の場合はスキップ
							const $h2 = $('<h2>', { 'id': 'denkiyohouToday', 'class': 'puTitlePrimary w100' });
							$h2.append(col);
							$divY.append($h2);
							return;
						}
						if (col === '-') return; // 値が「-」の場合はスキップ
						const replaced = col.replace(KOUIKI_LFC_FILE_PREFIX, ''); // プレフィックスを削除
						const yyyymm = replaced.replace(/\.csv$/i, '');
						if (yyyymm > ym) return; // 前月、前々月の場合はスキップ
						const yyyy = yyyymm.slice(0,4);
						const mm = parseInt(yyyymm.slice(4),10);
						const text = yyyy + '年' + mm + '月';
						$divM.append(downloadHistoricalDataCreateLink(col, text));
						flag = true;
					});
					if (flag) {
						$('#download_historical_data').append($divY);
					}
					$('#download_historical_data').append($divM);
				});
				$('#download_historical_data').show();
			}
		}
	};
	xhr.send(null);
}
