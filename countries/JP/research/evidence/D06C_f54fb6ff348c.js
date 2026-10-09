(async () => {

	const lang = ((lang) => lang === 'denkiyoho' ? 'ja' : lang.substring(0, 2))(location.pathname.split('/').at(1));
	const document_name = location.pathname.replace(/\/$/,'/index.html').split('/').pop();

	const mixins = {
		methods: {
			translate(...messages) {
				return messages[['ja', 'en'].indexOf(this.lang)]
			},
			isEmpty(item) {
				const type = typeof item,
					check = {
						string(v) {
							return v.length === 0;
						},
						object(v) {
							return Object.keys(v).length === 0 || Object.values(v).every((v2) => !v2);
						},
					};
				return Array.isArray(item) ? item.length === 0 : (!check[type] || check[type](item));
			},
		},
		data() {
			return {
				lang: lang,
				document_name:document_name
			}
		}
	}

	const { VueComponents } = await import('./module/vue-components.js')

	for (let [k, v] of Object.entries(VueComponents)) {
		v.mixins = [mixins]
	}

	const jsonMap = new Map(
		Array.from(document.querySelectorAll('[data-json-name]')).map(elem => [elem.dataset.jsonName, elem.dataset.jsonPath])
	),
	jsonKeys = Array.from(jsonMap.keys()).map(v=>v)

	const { createApp, ref, onMounted } = Vue

	const app = createApp({
		components: VueComponents,
		data() {
			return {
				sortkeys: [],
				emits: {},
				data: {}
			}
		},
		async created() {

			const results = await Promise.allSettled(Array.from(jsonMap.values()).map(url => axios.get(url)))

			const returndata = {};
		
			results.forEach(({status,value:{data}},i)=>{
				if(status !== 'fulfilled'){
					return true;
				}
				returndata[jsonKeys.at(i)] = data
			})

			this.data = returndata

		},
		methods: {
			call(object, original) {
				for ([key, value] of Object.entries(object)) {
					if (this[key] && typeof (this[key]) === 'object' && !original) {
						for (let [subkey, v] of Object.entries(value)) {
							this[key][subkey] = v
						}
					} else {
						this[key] = value
					}
				}
			},
		},
		mixins:[mixins],
		mounted() {
			this.sortkeys = this.$refs.legend ?
				Array.from(this.$refs.legend.querySelectorAll('.legend-item')).map(elem => elem.dataset.name)
				: []
		}

	})

	app.config.globalProperties.lang = lang
	app.mount('#app')

})()