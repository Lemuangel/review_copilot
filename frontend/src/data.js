// mockDB.js
// 模拟差评数据库 - 覆盖物流/尺码/色差/质量/客服/描述不符/包装/恶意差评等场景
// 用于前端独立开发和联调，真实接口上线后仅需替换 API 请求即可

export const mockReviews = [
  // ==================== 1. 物流问题（5条） ====================
  {
    id: 'R001',
    starRating: 1,
    commentText: 'Never received my package! Carrier lost it.',
    translatedText: '从未收到包裹！承运商弄丢了。',
    category: '物流问题',
    country: 'US',
    timestamp: '2026-07-10T14:23:00Z',
    verified: true,
    vineVoice: false,
    images: ['https://picsum.photos/seed/001/400/400'],
    logistics: {
      carrier: '燕文专线',
      trackingNumber: 'YW123456789',
      deliveryDays: 18,
      isDelayed: true,
      status: '已签收但未收到',
      events: ['2026-07-01 已揽收', '2026-07-05 清关异常', '2026-07-10 疑似丢包']
    },
    sku: 'ELEC-001',
    productAttribute: '无线耳机',
    customerHistory: { repeatBuy: false, returnRate: 0.1, badReviewFreq: 0.05 },
    aiSuggestion: '【物流建议】立即联系燕文客服查询丢包原因，向客户道歉并补发，同时考虑切换至更稳定的云途物流。',
    aiReply: 'Dear customer, we sincerely apologize for the lost package. We have contacted the carrier and will resend your order within 24 hours. Thank you for your patience.'
  },
  {
    id: 'R002',
    starRating: 2,
    commentText: 'Package arrived 10 days late, ruined my party.',
    translatedText: '包裹晚了10天，毁了我的派对。',
    category: '物流问题',
    country: 'DE',
    timestamp: '2026-07-08T09:15:00Z',
    verified: true,
    vineVoice: false,
    images: [],
    logistics: {
      carrier: '云途全球',
      trackingNumber: 'YT987654321',
      deliveryDays: 22,
      isDelayed: true,
      status: '已送达但严重延迟',
      events: ['2026-06-20 出关', '2026-06-28 德国海关扣件', '2026-07-08 最终投递']
    },
    sku: 'PARTY-005',
    productAttribute: '气球装饰',
    customerHistory: { repeatBuy: false, returnRate: 0, badReviewFreq: 0 },
    aiSuggestion: '【物流建议】德国海关近期严查，建议提前准备报关文件，或改用DHL特快线路。可向客户提供20%退款作为补偿。',
    aiReply: 'Hallo, wir entschuldigen uns für die Verspätung. Die Zollabfertigung hat länger gedauert. Wir bieten Ihnen eine 20% Rückerstattung an.'
  },
  {
    id: 'R003',
    starRating: 1,
    commentText: 'Says delivered but I checked my porch 5 times. Nothing there.',
    translatedText: '显示已送达，但我去门口看了5次，什么都没有。',
    category: '物流问题',
    country: 'US',
    timestamp: '2026-07-05T20:10:00Z',
    verified: true,
    vineVoice: false,
    images: ['https://picsum.photos/seed/003/400/400'],
    logistics: {
      carrier: 'USPS',
      trackingNumber: 'USPS88888888',
      deliveryDays: 7,
      isDelayed: false,
      status: '已签收但未收到（疑似盗件）',
      events: ['2026-06-28 发出', '2026-07-04 到达当地', '2026-07-05 显示已签收']
    },
    sku: 'HOME-012',
    productAttribute: '智能门铃',
    customerHistory: { repeatBuy: true, returnRate: 0, badReviewFreq: 0 },
    aiSuggestion: '【物流建议】建议客户联系当地警局报案，同时我们立即启动索赔流程并向客户补发，下次需勾选“本人签收”选项。',
    aiReply: 'We are very sorry to hear that. Please confirm with your family/neighbors. If still missing, we will file a claim with USPS and resend it to you.'
  },
  {
    id: 'R004',
    starRating: 2,
    commentText: 'Stuck in customs for 2 weeks. Terrible experience.',
    translatedText: '在海关卡了两周，体验极差。',
    category: '物流问题',
    country: 'JP',
    timestamp: '2026-07-04T02:30:00Z',
    verified: false,
    vineVoice: false,
    images: [],
    logistics: {
      carrier: '日本专线',
      trackingNumber: 'JP11223344',
      deliveryDays: 16,
      isDelayed: true,
      status: '清关延误',
      events: ['2026-06-20 抵达日本', '2026-06-22 海关查验', '2026-07-04 放行']
    },
    sku: 'BEAUTY-007',
    productAttribute: '液体化妆品',
    customerHistory: { repeatBuy: false, returnRate: 0.2, badReviewFreq: 0.1 },
    aiSuggestion: '【物流建议】发往日本的液体产品需提前提供MSDS成分表，下次使用亚马逊FBA渠道可避免清关主体责任。',
    aiReply: '申し訳ございません。通関手続きに時間がかかりました。次回はより迅速な配送方法を選択いたします。'
  },
  {
    id: 'R005',
    starRating: 3,
    commentText: 'Shipping took forever, I almost forgot I ordered this.',
    translatedText: '运输花了一个世纪，我差点忘了我买过这个。',
    category: '物流问题',
    country: 'AU',
    timestamp: '2026-07-01T23:59:00Z',
    verified: true,
    vineVoice: false,
    images: [],
    logistics: {
      carrier: '澳洲专线',
      trackingNumber: 'AU44556677',
      deliveryDays: 28,
      isDelayed: true,
      status: '超长运输',
      events: ['2026-06-03 揽收', '2026-06-15 中转', '2026-07-01 妥投']
    },
    sku: 'TOY-003',
    productAttribute: '毛绒玩具',
    customerHistory: { repeatBuy: false, returnRate: 0.05, badReviewFreq: 0.02 },
    aiSuggestion: '【物流建议】澳洲线建议备货至悉尼海外仓，可缩短至5-7天，提高客户满意度。',
    aiReply: "We apologize for the long shipping time. We're now setting up an Australian warehouse to solve this problem."
  },

  // ==================== 2. 尺码问题（4条） ====================
  {
    id: 'R006',
    starRating: 2,
    commentText: 'The shoes are too narrow, fit is terrible. My feet hurt just trying them on.',
    translatedText: '鞋子太窄了，穿上脚疼得不行。',
    category: '尺码问题',
    country: 'US',
    timestamp: '2026-07-12T11:20:00Z',
    verified: true,
    vineVoice: true,
    images: ['https://picsum.photos/seed/006/400/400'],
    logistics: { carrier: '云途', trackingNumber: 'YT001006', deliveryDays: 6, isDelayed: false, status: '已签收' },
    sku: 'SHOE-42-BLACK',
    productAttribute: '窄版/尖头',
    customerHistory: { repeatBuy: false, returnRate: 0, badReviewFreq: 0 },
    aiSuggestion: '【产品建议】建议在尺码表中增加“脚宽（Width）”参数，并附上测量教程，同时增加宽版（Wide）变体选项。',
    aiReply: 'We are sorry the fit is not right. We suggest you try our "Wide" version. We will send you a return label for this pair.'
  },
  {
    id: 'R007',
    starRating: 1,
    commentText: 'This dress is so small! I ordered M but it looks like XS.',
    translatedText: '这条裙子太小了！我买的M码，看起来像XS。',
    category: '尺码问题',
    country: 'UK',
    timestamp: '2026-07-11T08:45:00Z',
    verified: true,
    vineVoice: false,
    images: ['https://picsum.photos/seed/007/400/400', 'https://picsum.photos/seed/077/400/400'],
    logistics: { carrier: '皇家邮政', trackingNumber: 'RM007007', deliveryDays: 5, isDelayed: false, status: '已签收' },
    sku: 'DRESS-2026-M',
    productAttribute: '修身连衣裙',
    customerHistory: { repeatBuy: false, returnRate: 0.3, badReviewFreq: 0.1 },
    aiSuggestion: '【产品建议】立即检查该批次尺码标是否贴错，并修改Listing尺码表，加入胸围/腰围具体厘米数，而非仅标注S/M/L。',
    aiReply: 'We apologize for the size issue. Our M size runs a bit small. We will send you an L size replacement today, free of charge.'
  },
  {
    id: 'R008',
    starRating: 3,
    commentText: 'Pants are way too long, even with high heels.',
    translatedText: '裤子太长了，穿高跟鞋都拖地。',
    category: '尺码问题',
    country: 'DE',
    timestamp: '2026-07-09T15:30:00Z',
    verified: true,
    vineVoice: false,
    images: [],
    logistics: { carrier: 'DHL', trackingNumber: 'DHL998877', deliveryDays: 4, isDelayed: false, status: '已签收' },
    sku: 'PANT-38-L',
    productAttribute: '长裤/标准长度',
    customerHistory: { repeatBuy: false, returnRate: 0, badReviewFreq: 0 },
    aiSuggestion: '【产品建议】欧洲人腿长比例与亚洲不同，建议针对欧洲站点提供“短版/常规版/长版”三种长度选项。',
    aiReply: 'Es tut uns leid. Wir bieten jetzt 3 Längenoptionen an. Bitte teilen Sie uns Ihre gewünschte Länge mit, wir erstatten die Differenz.'
  },
  {
    id: 'R009',
    starRating: 2,
    commentText: 'The size chart is completely misleading. I measured myself but still got a huge shirt.',
    translatedText: '尺码表完全误导人，我量了尺寸还是买了件巨大的T恤。',
    category: '尺码问题',
    country: 'FR',
    timestamp: '2026-07-06T12:00:00Z',
    verified: false,
    vineVoice: false,
    images: ['https://picsum.photos/seed/009/400/400'],
    logistics: { carrier: '云途', trackingNumber: 'YT009009', deliveryDays: 8, isDelayed: false, status: '已签收' },
    sku: 'TSHIRT-XXL',
    productAttribute: '宽松版',
    customerHistory: { repeatBuy: false, returnRate: 0.1, badReviewFreq: 0 },
    aiSuggestion: '【产品建议】更新尺码表为“成衣平铺测量”数据（肩宽/胸围/衣长），而非推荐身高体重，并增加视频测量教程。',
    aiReply: 'Bonjour, nous sommes désolés pour le guide des tailles. Nous avons mis à jour les mesures précises sur la page. Nous vous remboursons la moitié du montant.'
  },

  // ==================== 3. 颜色色差（3条） ====================
  {
    id: 'R010',
    starRating: 1,
    commentText: 'The color is totally different! I ordered Red but got Pink. Horrible.',
    translatedText: '颜色完全不一样！我买的是红色，收到的是粉色。太糟糕了。',
    category: '颜色色差',
    country: 'US',
    timestamp: '2026-07-13T18:00:00Z',
    verified: true,
    vineVoice: true,
    images: ['https://picsum.photos/seed/010/400/400', 'https://picsum.photos/seed/101/400/400'],
    logistics: { carrier: 'USPS', trackingNumber: 'USPS101010', deliveryDays: 3, isDelayed: false, status: '已签收' },
    sku: 'BAG-001-RED',
    productAttribute: '红色（PANTONE 185C）',
    customerHistory: { repeatBuy: false, returnRate: 0, badReviewFreq: 0 },
    aiSuggestion: '【产品建议】请校准主图颜色显示（显示器色差），并在描述中注明“由于光线原因可能存在轻微色差”，同时附上室内室外实拍对比图。',
    aiReply: 'We are sorry for the color difference. We have updated the images to reflect the true color. We will give you a full refund and you may keep the bag.'
  },
  {
    id: 'R011',
    starRating: 2,
    commentText: 'Looks like a cheap knockoff, the blue is so dull compared to the picture.',
    translatedText: '看起来像廉价山寨货，蓝色比图片暗淡太多了。',
    category: '颜色色差',
    country: 'JP',
    timestamp: '2026-07-08T06:00:00Z',
    verified: true,
    vineVoice: false,
    images: ['https://picsum.photos/seed/011/400/400'],
    logistics: { carrier: '日本专线', trackingNumber: 'JP011011', deliveryDays: 5, isDelayed: false, status: '已签收' },
    sku: 'CUSHION-02',
    productAttribute: '天蓝色',
    customerHistory: { repeatBuy: true, returnRate: 0.1, badReviewFreq: 0.05 },
    aiSuggestion: '【产品建议】可能是布料批次差异导致，建议排查供应链染料批次，并在Listing中增加“实拍无滤镜”视频。',
    aiReply: '申し訳ございません。実物の色味について商品ページを修正しました。次回ご購入時に10%割引いたします。'
  },
  {
    id: 'R012',
    starRating: 3,
    commentText: 'The material looks different. Shiny in the photo, matte in real life.',
    translatedText: '材质看起来不一样，图片是亮面的，实物是哑光的。',
    category: '颜色色差',
    country: 'CA',
    timestamp: '2026-07-04T19:00:00Z',
    verified: false,
    vineVoice: false,
    images: ['https://picsum.photos/seed/012/400/400'],
    logistics: { carrier: '加拿大专线', trackingNumber: 'CA121212', deliveryDays: 10, isDelayed: true, status: '已签收' },
    sku: 'JACKET-03',
    productAttribute: '哑光尼龙',
    customerHistory: { repeatBuy: false, returnRate: 0, badReviewFreq: 0 },
    aiSuggestion: '【产品建议】修改主图为室内光源下实物拍摄，并在A+页面中注明面料质感（哑光/亮面）。',
    aiReply: 'We apologize for the material perception. We have updated the listing with video showing the actual texture. We offer a partial refund for this difference.'
  },

  // ==================== 4. 质量/功能问题（4条） ====================
  {
    id: 'R013',
    starRating: 1,
    commentText: 'The speaker stopped working after just 3 days. Completely dead.',
    translatedText: '扬声器用了3天就坏了，彻底没声音了。',
    category: '质量问题',
    country: 'DE',
    timestamp: '2026-07-14T10:00:00Z',
    verified: true,
    vineVoice: false,
    images: ['https://picsum.photos/seed/013/400/400'],
    logistics: { carrier: 'DHL', trackingNumber: 'DHL131313', deliveryDays: 4, isDelayed: false, status: '已签收' },
    sku: 'SPK-100-BLK',
    productAttribute: '蓝牙5.0',
    customerHistory: { repeatBuy: false, returnRate: 0, badReviewFreq: 0 },
    aiSuggestion: '【产品建议】立即锁定该批次（Batch#202606），检查PCB板焊接工艺，建议延长保修期至18个月以挽回信誉。',
    aiReply: 'Wir bedauern den Defekt. Wir senden Ihnen sofort ein neues Gerät zu. Bitte entsorgen Sie das defekte Gerät nicht, wir schicken ein Retourenetikett.'
  },
  {
    id: 'R014',
    starRating: 2,
    commentText: 'The glass cup broke just by pouring hot water into it. Dangerous!',
    translatedText: '玻璃杯倒热水进去就炸了！太危险了！',
    category: '质量问题',
    country: 'US',
    timestamp: '2026-07-07T13:45:00Z',
    verified: true,
    vineVoice: false,
    images: ['https://picsum.photos/seed/014/400/400', 'https://picsum.photos/seed/141/400/400'],
    logistics: { carrier: '云途', trackingNumber: 'YT014014', deliveryDays: 5, isDelayed: false, status: '已签收' },
    sku: 'GLASS-001',
    productAttribute: '高硼硅玻璃',
    customerHistory: { repeatBuy: false, returnRate: 0.2, badReviewFreq: 0.1 },
    aiSuggestion: '【产品建议】排查是否误用了钠钙玻璃代替高硼硅，需提供供应商质检报告。上架前增加抗热震性测试。',
    aiReply: 'We are extremely sorry for this hazardous issue. We will issue a full refund immediately and investigate our supplier.'
  },
  {
    id: 'R015',
    starRating: 3,
    commentText: 'The color faded after one wash. Totally ruined my white shirt.',
    translatedText: '洗一次就掉色了，把我的白衬衫全染了。',
    category: '质量问题',
    country: 'FR',
    timestamp: '2026-07-05T11:00:00Z',
    verified: true,
    vineVoice: false,
    images: ['https://picsum.photos/seed/015/400/400'],
    logistics: { carrier: '法国专线', trackingNumber: 'FR151515', deliveryDays: 6, isDelayed: false, status: '已签收' },
    sku: 'JEANS-2026',
    productAttribute: '深蓝牛仔',
    customerHistory: { repeatBuy: false, returnRate: 0.4, badReviewFreq: 0.2 },
    aiSuggestion: '【产品建议】牛仔面料色牢度不达标，需增加固色工艺，并在洗标中强调“冷水单独洗涤”。',
    aiReply: 'Bonjour, nous sommes désolés pour ce problème de décoloration. Nous vous remboursons intégralement et allons améliorer le processus de teinture.'
  },
  {
    id: 'R016',
    starRating: 2,
    commentText: 'Strong chemical smell when opened. Gave me a headache.',
    translatedText: '打开有强烈的化学气味，闻得我头痛。',
    category: '质量问题',
    country: 'US',
    timestamp: '2026-07-03T22:00:00Z',
    verified: false,
    vineVoice: false,
    images: [],
    logistics: { carrier: 'USPS', trackingNumber: 'USPS161616', deliveryDays: 4, isDelayed: false, status: '已签收' },
    sku: 'MAT-101',
    productAttribute: '瑜伽垫-PVC材质',
    customerHistory: { repeatBuy: false, returnRate: 0.1, badReviewFreq: 0 },
    aiSuggestion: '【产品建议】立即更换环保TPE材质，而非低价PVC。仓库需增加通风晾晒工序再打包。',
    aiReply: 'We apologize for the smell. We have switched to eco-friendly TPE material. We will send you a new one free of charge.'
  },

  // ==================== 5. 客服问题（3条） ====================
  {
    id: 'R017',
    starRating: 1,
    commentText: 'Customer service never replied to my emails. Extremely frustrating.',
    translatedText: '客服从来不回我邮件，烦死了。',
    category: '客服问题',
    country: 'UK',
    timestamp: '2026-07-12T17:00:00Z',
    verified: true,
    vineVoice: false,
    images: [],
    logistics: { carrier: '皇家邮政', trackingNumber: 'RM171717', deliveryDays: 5, isDelayed: false, status: '已签收' },
    sku: 'PHONE-09',
    productAttribute: '手机壳',
    customerHistory: { repeatBuy: true, returnRate: 0, badReviewFreq: 0 },
    aiSuggestion: '【客服建议】检查工单系统是否漏单，建议设置自动回复+24小时响应SLA，并立即指派专人跟进该客户。',
    aiReply: 'We sincerely apologize for the delayed response. Our team has been swamped but we are implementing an auto-reply system. We have emailed you directly with a solution.'
  },
  {
    id: 'R018',
    starRating: 2,
    commentText: 'Asked for a refund 3 weeks ago. Still no money back.',
    translatedText: '3周前申请的退款，到现在还没收到钱。',
    category: '客服问题',
    country: 'AU',
    timestamp: '2026-07-10T04:00:00Z',
    verified: true,
    vineVoice: false,
    images: ['https://picsum.photos/seed/018/400/400'],
    logistics: { carrier: '澳洲专线', trackingNumber: 'AU181818', deliveryDays: 12, isDelayed: true, status: '已签收' },
    sku: 'CABLE-002',
    productAttribute: '数据线',
    customerHistory: { repeatBuy: false, returnRate: 0.5, badReviewFreq: 0.1 },
    aiSuggestion: '【客服建议】财务处理效率低下，建议启用PayPal/支付宝一键退款功能，并补偿客户20%优惠券。',
    aiReply: "We apologize for the delay in refund. Our finance team has processed it now. You'll receive the money within 48 hours. Extra 30% off coupon attached."
  },
  {
    id: 'R019',
    starRating: 3,
    commentText: 'The agent was rude and hung up on me.',
    translatedText: '客服态度很差，直接挂我电话。',
    category: '客服问题',
    country: 'CA',
    timestamp: '2026-07-06T16:30:00Z',
    verified: false,
    vineVoice: false,
    images: [],
    logistics: { carrier: '加拿大专线', trackingNumber: 'CA191919', deliveryDays: 7, isDelayed: false, status: '已签收' },
    sku: 'LAMP-04',
    productAttribute: '台灯',
    customerHistory: { repeatBuy: false, returnRate: 0, badReviewFreq: 0 },
    aiSuggestion: '【客服建议】对该客服进行再培训，并引入“差评预警”机制——若客户工单未解决，自动升级至主管处理。',
    aiReply: 'We are deeply sorry for the rudeness. That agent has been retrained. We hope you give us another chance. Full refund has been issued.'
  },

  // ==================== 6. 描述不符（3条） ====================
  {
    id: 'R020',
    starRating: 2,
    commentText: 'It says 100% Cotton, but it feels like 100% Polyester. Sweating badly.',
    translatedText: '标着100%纯棉，摸起来像100%涤纶，穿着狂出汗。',
    category: '描述不符',
    country: 'US',
    timestamp: '2026-07-11T10:20:00Z',
    verified: true,
    vineVoice: false,
    images: ['https://picsum.photos/seed/020/400/400'],
    logistics: { carrier: '云途', trackingNumber: 'YT020020', deliveryDays: 4, isDelayed: false, status: '已签收' },
    sku: 'TSHIRT-100',
    productAttribute: '白色圆领',
    customerHistory: { repeatBuy: false, returnRate: 0.1, badReviewFreq: 0.1 },
    aiSuggestion: '【产品建议】核查该批次面料成分报告，若检测不符需立即下架并修改Listing材质描述，避免“货不对板”投诉升级。',
    aiReply: 'We apologize for the material discrepancy. We have updated the listing to reflect the true composition. We are sending you a 100% Cotton replacement.'
  },
  {
    id: 'R021',
    starRating: 1,
    commentText: 'The listing shows 3 functions, but this only has 1 button. Scam!',
    translatedText: '描述有3种功能，实际只有1个按键，骗子！',
    category: '描述不符',
    country: 'DE',
    timestamp: '2026-07-09T08:00:00Z',
    verified: true,
    vineVoice: true,
    images: ['https://picsum.photos/seed/021/400/400'],
    logistics: { carrier: 'DHL', trackingNumber: 'DHL212121', deliveryDays: 5, isDelayed: false, status: '已签收' },
    sku: 'LIGHT-03',
    productAttribute: '多功能手电',
    customerHistory: { repeatBuy: false, returnRate: 0, badReviewFreq: 0 },
    aiSuggestion: '【产品建议】可能是发错了旧版库存，立即排查FBA库存批次。建议发送新版替换，并向客户道歉。',
    aiReply: 'Wir haben die falsche Version gesendet. Die richtige Version mit 3 Funktionen wird Ihnen morgen zugestellt. Bitte behalten Sie die alte Version.'
  },
  {
    id: 'R022',
    starRating: 3,
    commentText: 'The size in the title says 40cm, but it is only 35cm. Cheated.',
    translatedText: '标题写着40cm，实际只有35cm，被骗了。',
    category: '描述不符',
    country: 'JP',
    timestamp: '2026-07-07T01:00:00Z',
    verified: true,
    vineVoice: false,
    images: ['https://picsum.photos/seed/022/400/400', 'https://picsum.photos/seed/222/400/400'],
    logistics: { carrier: '日本专线', trackingNumber: 'JP222222', deliveryDays: 6, isDelayed: false, status: '已签收' },
    sku: 'PLUSH-01',
    productAttribute: '大号公仔',
    customerHistory: { repeatBuy: false, returnRate: 0.2, badReviewFreq: 0 },
    aiSuggestion: '【产品建议】检查标题和实际尺寸是否因单位换算错误（英寸混淆厘米），立即统一修正所有站点的尺寸单位。',
    aiReply: '申し訳ございません。サイズ表記に誤りがありました。返金対応いたしますとともに、商品ページを修正いたしました。'
  },

  // ==================== 7. 包装问题（2条） ====================
  {
    id: 'R023',
    starRating: 2,
    commentText: 'The box was crushed, the corners of the frame are bent.',
    translatedText: '盒子压扁了，画框的角都弯了。',
    category: '包装问题',
    country: 'UK',
    timestamp: '2026-07-08T14:00:00Z',
    verified: true,
    vineVoice: false,
    images: ['https://picsum.photos/seed/023/400/400'],
    logistics: { carrier: '皇家邮政', trackingNumber: 'RM232323', deliveryDays: 5, isDelayed: false, status: '已签收' },
    sku: 'FRAME-01',
    productAttribute: '木质画框',
    customerHistory: { repeatBuy: false, returnRate: 0, badReviewFreq: 0 },
    aiSuggestion: '【包装建议】易碎/易弯折产品应使用蜂窝纸板或护角条，外箱需贴“易碎品”标识，并投保运输险。',
    aiReply: 'We apologize for the damaged packaging. We are upgrading our packaging with corner protectors. A full refund has been sent to you.'
  },
  {
    id: 'R024',
    starRating: 3,
    commentText: 'The bottle leaked everywhere, wasted half of the product.',
    translatedText: '瓶子漏得到处都是，浪费了一半。',
    category: '包装问题',
    country: 'US',
    timestamp: '2026-07-06T09:30:00Z',
    verified: true,
    vineVoice: false,
    images: ['https://picsum.photos/seed/024/400/400'],
    logistics: { carrier: 'USPS', trackingNumber: 'USPS242424', deliveryDays: 3, isDelayed: false, status: '已签收' },
    sku: 'OIL-005',
    productAttribute: '精油瓶装',
    customerHistory: { repeatBuy: true, returnRate: 0, badReviewFreq: 0 },
    aiSuggestion: '【包装建议】瓶口增加铝箔封口膜，并使用独立防漏袋包装。建议内盒增加缓冲材料防止挤压爆裂。',
    aiReply: 'We are sorry for the leak. We have reinforced the sealing process. We will resend a full new bottle to you immediately.'
  },

  // ==================== 8. 综合/恶意差评（1条） ====================
  {
    id: 'R025',
    starRating: 1,
    commentText: 'Worst product ever. Just bad. (No specific reason)',
    translatedText: '史上最差产品，就是烂。（没说具体原因）',
    category: '综合（疑似恶意）',
    country: 'US',
    timestamp: '2026-07-02T20:00:00Z',
    verified: false,
    vineVoice: false,
    images: [],
    logistics: { carrier: '云途', trackingNumber: 'YT252525', deliveryDays: 6, isDelayed: false, status: '已签收' },
    sku: 'RANDOM-01',
    productAttribute: '通用配件',
    customerHistory: { repeatBuy: false, returnRate: 0.8, badReviewFreq: 0.9 },
    aiSuggestion: '【风控建议】该买家历史差评率90%，退货率80%，建议标记为高风险恶意买家。不提供补偿，只做礼貌性回复，并点击“举报滥用评论”。',
    aiReply: 'We are sorry you feel that way. We take all feedback seriously. If you have any specific issue, please contact us so we can help.'
  }
];

// ============ 工具函数：模拟 API 接口（供前端开发调用） ============

// 模拟延迟
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// 1. 获取差评列表（支持分页、分类筛选、关键词搜索）
export const fetchMockReviews = async (params = {}) => {
  await delay(300);
  let result = [...mockReviews];

  // 分类筛选
  if (params.category && params.category !== 'all') {
    result = result.filter(item => item.category === params.category);
  }

  // 关键词搜索（评论内容）
  if (params.keyword) {
    const kw = params.keyword.toLowerCase();
    result = result.filter(item =>
      item.commentText.toLowerCase().includes(kw) ||
      item.translatedText.includes(kw)
    );
  }

  // 国家筛选
  if (params.country) {
    result = result.filter(item => item.country === params.country);
  }

  // 分页
  const page = params.page || 1;
  const size = params.size || 10;
  const start = (page - 1) * size;
  const end = start + size;

  return {
    code: 200,
    data: result.slice(start, end),
    total: result.length,
    page: page,
    size: size
  };
};

// 2. 获取单条差评详情（根据 ID）
export const fetchMockReviewDetail = async (id) => {
  await delay(200);
  const found = mockReviews.find(item => item.id === id);
  if (found) {
    return { code: 200, data: found };
  } else {
    throw { code: 404, message: '差评未找到' };
  }
};

// 3. 获取统计数据（用于 ECharts 图表）
export const fetchMockStatistics = async () => {
  await delay(200);
  const categories = {};
  const countries = {};

  mockReviews.forEach(item => {
    categories[item.category] = (categories[item.category] || 0) + 1;
    countries[item.country] = (countries[item.country] || 0) + 1;
  });

  // 星级分布
  const starDistribution = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
  mockReviews.forEach(item => {
    starDistribution[item.starRating] = (starDistribution[item.starRating] || 0) + 1;
  });

  return {
    code: 200,
    data: {
      total: mockReviews.length,
      categories: Object.keys(categories).map(key => ({ name: key, value: categories[key] })),
      countries: Object.keys(countries).map(key => ({ name: key, value: countries[key] })),
      starDistribution: Object.keys(starDistribution).map(key => ({ star: key, count: starDistribution[key] }))
    }
  };
};

// src/data.js 最后一行
export default mockReviews;   // 改成默认导出