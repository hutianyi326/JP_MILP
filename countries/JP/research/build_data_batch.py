import pathlib,json,re,urllib.parse
B=pathlib.Path(__file__).resolve().parent
jobs=[]
months=[f'{y}{m:02}' for y in [2025,2026] for m in range(1,13) if f'{y}{m:02}'<='202608']
# Templates observed in official links or their public download scripts.
templates={
'01':'https://www.hepco.co.jp/network/con_service/public_document/supply_demand_results/csv/eria_jukyu_{m}_01.csv',
'05':'https://www.rikuden.co.jp/nw/denki-yoho/csv/eria_jukyu_{m}_05.csv',
'08':'https://www.yonden.co.jp/nw/supply_demand/csv/eria_jukyu_{m}_08.csv'}
for a,t in templates.items():
 for m in months:jobs.append({'id':f'TS{a}_{m}','url':t.format(m=m),'area':a,'month':m})
extra=[
('D04C','https://powergrid.chuden.co.jp/denkiyoho/resource/js/create-download-link.js'),
('D06D','https://www.kansai-td.co.jp/interchange/denkiyoho/area-performance/filelist.json'),
('D09C','https://www.kyuden.co.jp/td_area_jukyu/csv/eria_jukyu_nendo_list.csv'),
('J07','https://www.jepx.jp/js/get_graph_year.php?dir=spot_summary'),
('J08','https://www.jepx.jp/market/excel/spot_2025.csv'),
('E11','https://www.eprx.or.jp/j_information/docs/250328_news.pdf'),
('L02','https://www.tepco.co.jp/pg/consignment/workshop/procedure/renewable/fit/pdf/koatu_tikudenti.pdf')]
jobs +=[{'id':i,'url':u} for i,u in extra]
(B/'batch04.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf-8')
print(len(jobs))

jobs=[]
for a,t in {
'06':'https://www.kansai-td.co.jp/interchange/denkiyoho/area-performance/eria_jukyu_{m}_06.csv',
'07':'https://www.energia.co.jp/nw/jukyuu/sys/eria_jukyu_{m}_07.csv',
'09':'https://www.kyuden.co.jp/td_area_jukyu/csv/eria_jukyu_{m}_09.csv'}.items():
 for m in months:jobs.append({'id':f'TS{a}_{m}','url':t.format(m=m),'area':a,'month':m})
extra=[
('J09','https://www.jepx.jp/market/excel/spot_2024.csv'),
('J10','https://www.jepx.jp/market/excel/spot_2026.csv'),
('J11','https://www.jepx.jp/electricpower/market-data/intraday/'),
('D04D','https://powergrid.chuden.co.jp/denkiyoho/resource/js/get-data.js'),
('D02B','https://setsuden.nw.tohoku-epco.co.jp/realtime_jukyu.html'),
('E12','https://www.eprx.or.jp/information/post.php'),
('E13','https://www.occto.or.jp/iinkai/chouseiryoku/jukyuchousei/2025/files/jukyu_shijyo_56_05.pdf'),
('E14','https://www.occto.or.jp/assets/iinkai/chouseiryoku/jukyuchousei/2024/files/jukyu_shijyo_51_04.pdf'),
('O07','https://www.occto.or.jp/assets/market-board/market/jitsujukyukanren/files/250328_mainauction_boshuyoukou_jitsujukyu2025.pdf'),
('O08','https://www.occto.or.jp/assets/market-board/market/jitsujukyukanren/files/250328_tsuikaauction_boshuyoukou_jitsujukyu2025.pdf'),
('O09','https://www.occto.or.jp/various/capacity-market/jitsujukyukanren/2026_jitsujukyu_kanren.html'),
('E15','https://www.eprx.or.jp/outline/docs/kaitou_250213.pdf'),
('E16','https://www.eprx.or.jp/outline/docs/kaitou_251211r.pdf')]
jobs +=[{'id':i,'url':u} for i,u in extra]
(B/'batch05.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf-8')
print(len(jobs))
