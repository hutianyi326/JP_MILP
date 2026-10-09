// 年選択イベント処理
function selectYear() {
    var cmbYear  = document.frmDL.year;
    var cmbMonth = document.frmDL.month;

    setMonthList(cmbMonth, cmbYear.value);
}

// ダウンロードボタンクリックイベント
function downloadPastCsv() {
    // 日が未選択の場合
    if(document.frmDL.month.value==0) {
        alert('日付を指定してください。');
        return false;
    }
    var strYMD = document.frmDL.year.value
               + ('0' + document.frmDL.month.value).slice(-2);
    location.href = '/nw/denki-yoho/csv/eria_jukyu_' + strYMD + '_05.csv';
    return false;
}

// 年選択リストの設定
function setYearList(cmbYear) {
    // 選択リストのクリア
    cmbYear.length = 1;
    // 日付の大小が逆転の場合
    if(_dtMax < _dtMin) {
        return;
    }

    var intYearStart = _dtMin.getFullYear();
    var intYearEnd   = _dtMax.getFullYear();
    // 選択リストの追加
    cmbYear.length = (intYearEnd-intYearStart) + 2;
    for(i=0; i<=(intYearEnd-intYearStart); i++) {
        cmbYear.options[i+1].text  = i + intYearStart;
        cmbYear.options[i+1].value = i + intYearStart;
    }
}

// 月選択リストの設定
function setMonthList(cmbMonth, intYear) {
    // 選択リストのクリア
    cmbMonth.length = 1;
    // 年または月が未選択の場合
    if(intYear==0) {
        return;
    }

    var intMonthStart = 1;
    var intMonthEnd   = 12;
    // 開始日と同じ年の場合
    if(intYear==_dtMin.getFullYear()) {
        intMonthStart = _dtMin.getMonth() + 1;
    }
    // 終了日と同じ年の場合
    if(intYear==_dtMax.getFullYear()) {
        intMonthEnd = _dtMax.getMonth() + 1;
    }
    // 選択リストの追加
    cmbMonth.length = (intMonthEnd-intMonthStart) + 2;
    for(i=0; i<=(intMonthEnd-intMonthStart); i++) {
        cmbMonth.options[i+1].value = i + intMonthStart;
        cmbMonth.options[i+1].text  = i + intMonthStart;
    }
}
