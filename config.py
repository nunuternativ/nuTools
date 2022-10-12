# tool directory
TOOL_DIR = 'O:/studioTools/maya/python/tool/rig/nuTools'
TEMPLATE_DIR = 'O:/studioTools/maya/python/tool/rig/nuTools/template'
BTP_DIR = 'O:/studioTools/maya/python/tool/rig/nuTools/btp'
BSH_PUB_LOG_DIR = 'O:/studioTools/maya/python/tool/rig/tmp/bshPublish.log'
RIG_MOD_PKG_DIR = {'pkmel':'O:/studioTools/maya/python/tool/rig/pkmel', 
				'nuTools.rigTools':'O:/studioTools/maya/python/tool/rig/nuTools/rigTools'}



# tool filter
RIG_MOD_FILTER = ['crm_ui', 'weightTools', 'weightPuller', 'rigTools', 'core', 'ctrlShapeTools', 'controlMaker', 'skinTools', 'matcher', 'baseRig']
TEMP_CLS_FILTER = ['TempJoint', 'TempJoints', 'MirrorTempConnection']
ASSET_TYPE_FILTER = ['_textures', '_temp', 'images', 'light', 'mattePaint', 'movies', 'particles', 'renderData']
FILM_EP_FILTER = ['temp', 'edit', 'comment']



# drag sync context tool config
frd_syncInfo = {
	1:{'none'       :   {   'x':[   ('crnrMouthIO', 1), ('mouthClench', 0.225), ('loLipsCurlIO', -0.1), ('upLipsCurlIO',-0.1), ('mouthPull', -0.225), ('cheekIO', 0.1),],
                            'y':[   ('crnrMouthUD', 1), ('cheekLwrIO', 0.334), ('upLipsUD', 0.1667), ('loLipsUD', 0.1667), ('puffIO', 0.1), ('cheekIO', -0.1), ('ebInnerUD', 1), ('ebMidUD', 0.334), ('ebOuterUD', 0.125), ('upLidTW', 0.1), ('loLidTW', 0.05)]}, 
        'ctrl'      :   {   'x':[   ('lipsPartIO', 0.5)],
                            'y':[   ('loLipsUD', 1), ('loLidUD', 1)]},
        'shift'     :   {   'x':[   ('lipsPartIO', 0.5)],
                            'y':[   ('upLipsUD', 1), ('upLidUD', 1)]}},
    2:{ 'none'      :   {   'x':[   ('rotateY', 1), ('ebIO', 1)],
                            'y':[   ('rotateX', -1), ('mouthUD', 0.1), ('ebUD', 1)]},
        'ctrl'      :   {   'x':[   ('translateX', 0.0334)],
                            'y':[   ('translateY', 0.0334)]},
        'shift'     :   {   'x':[   ('mouthLR', 1), ('cheekIO', 0.1)],
                            'y':[   ('mouthUD', 1), ('cheekLwrIO', 0.1)]}}}



NODE_TYPE_DICT = {	'multiplyDivide':'mdv', 
					'multDoubleLinear':'mdl',
					'plusMinusAverage':'pma',
					'avgCurves':'avgCrvs',
					'addDoubleLinear':'adl',
					'blendColors':'bcol',
					'blendTwoAttr':'btAttr',
					'condition':'cond',
					'clamp':'cmp',
					'curveInfo':'cif',
					'cluster':'cls',
					'curveFromSurfaceIso':'cfsi',
					'distanceBetween':'dist',
					'locator':'loc',
					'loft':'loft',
					'reverse':'rev',
					'pointOnSurfaceInfo':'posi',
					'pointOnCurveInfo':'poci',
					'polyEdgeToCurve':'plyEtc',
					'setRange':'sr',
					'blendShape':'bsh',
					'lattice':'lat',
					'pairBlend':'pBlnd',
					'polySmoothFace':'plySmf',
					'joint':'jnt',
					'skinCluster':'skc',
					'angleBetween':'anBtw',
					'decomposeMatrix':'dMtx',
					'ikHandle':'ikHndl',
					'vectorProduct':'vecPd',
					'wire':'wire',
					'wrap':'wrp'
}



# user
USER_DEPT_DICT = {
	'model'		:['Eye', 'Muu', 'Nu', 'Nung', 'Pear', 'Pui', 'Tle', 'Chat'],
	'uv'		:['kong', 'Nack', 'Nus'],
	'rig'		:['Aou', 'Nunu', 'Ken', 'Nun', 'Pride'],
	'pipeline'	:['Nook', 'Ob', 'Preaw', 'Ta'],
	'layout'	:['Aom', 'Aor', 'Cherry', 'Eak', 'Hector', 'Jate', 'Leng', 'Pomme'],
	'anim'		:['Alpha', 'Bank', 'Bird', 'Boat', 'Bong', 'Daii', 'David', 'Dew', 'Fah', 'Gluay', 'Ifran', 'Kla', 'Kwan', 'May', 'Oh', 'Pable',
				  'Pang', 'Pangz', 'Prome', 'Riccardo', 'Tong', 'Zin', 'Zohaib'],
	'light'		:['Arm', 'Aum', 'Fluke', 'Max', 'Name', 'Ome'],
	'fx'		:['Ram']
}



# project directory  projName : [projPath, {ep:subtype}]
PROJ_DIR_DICT = { 	
	# 'BANG'							: ['P:/BANG',
	# 	{'Coin'						: False, 
	# 	 'hummelFK'					: False,}],

	'Lego_Friends'					: ['P:/Lego_Friends', 
		{''							: True }],

	'Lego_Friends11'				: ['P:/Lego_Friends11', 
		{''							: True }],

	# 'Lego_Friends12'				: ['P:/Lego_Friends12', 
	# 	{''							: True }],

	'Lego_Friends2015'				: ['P:/Lego_Friends2015', 
		{''							: True }],

	'Lego_FriendsGT'				: ['P:/Lego_FriendsGT', 
		{''							: True }],

	'Lego_FRDCG'					: ['P:/Lego_FRDCG', 
		{''							: True }],	

	'Lego_City'						: ['P:/Lego_City', 
		{''							: True ,
		'2014_CityPolice' 			: False,
		'2015_CTYadvent' 			: False,}],

	'Lego_CTYCG'					:['P:/Lego_CTYCG',
		{''							:True}],

	'Lego_CTY2D'					:['P:/Lego_CTY2D',
		{''							:True}],

	'Lego_City2D'					: ['P:/Lego_City2D', 
		{''							: True }],

	'Lego_AngryBirds'				: ['P:/Lego_AngryBirds', 
		{''							: True }],	

	# 'Lego_Duplo'					: ['P:/Lego_Duplo', 
	# 	{''							: True }],

	# 'Phibious'						: ['P:/Phibious', 
	# 	{''							: True }],

	# 'STK'							: ['P:/STK', 
	# 	{''							: True }],

	'Lego_Frozen'					: ['P:/Lego_Frozen', 
		{''							: True }],
			
	'TVC_LEGO' 						: ['P:/TVC_LEGO', 
		{

		'Lego_Ninjago_s2015'		: False,
		'2015_NexoKnight_testTVC'	: False,
		'Lego_scoobyDoo_lf2015'		: False,
		'2015_LKT'					: False,
		'TVC_LNK_UK1HY16'			: False,
		'TVC_LNK_PLA1HY16'			: False,
		'TVC_LNK_PLB1HY16'			: False,
		'TVC_LNSB_1HY16'			: False,
		'TVC_LSHA_1HY16'			: False,
		'TVC_LSHB_1HY16'			: False,
		'TVC_LSHC_1HY16'			: False,
		'TVC_LN_USR_2HY16'			: False,
		'TVC_LNK_AXRB_2HY16'		: False,
		'TVC_LNK_AXTC_2HY16'		: False,
		'TVC_LNK_JLL_2HY16'			: False,
		'TVC_LSH_SPI_2HY16'			:False,
		
		}

		]


	# 'Lego_TVC' 						: ['P:/Lego_TVC', 
	# 	{'Lego_TMNT_2014'			: False,
	# 	'Lego_Ninjago_2014'			: False,
	# 	'Lego_ChimaSocialG_2014'	: False, 
	# 	'Lego_ChimaBAF_2014'		: False, 
	# 	'Lego_Movie_2014'			: False, 
	# 	'Lego_SuperheroGOTG_2014'	: False,
	# 	'Lego_ChimaPT1_2014'		: False,
	# 	'Lego_ChimaPT2_2014'		: False,
	# 	'Lego_Hobbit_pf2014'		: False,
	# 	'Lego_Ninjago_f2014'		: False,
	# 	'Lego_SuperHeroC_f2014'		: False,
	# 	'Lego_Chima_f2014'			: False,
	# 	'Lego_CTY_t2014'			: False,
	# 	'Lego_SuperHeroD_lf2014'	: False,
	# 	'Lego_Jurassic_lf2014'		: False}],

	# 	'twoWarts'					: ['P:/twoWarts',
		
	# 	{''							: True }]

	# 'x_archive'					: ['P:/x_archive', 
	# 	{''							: True }],

	# '2013_Fall_LOTR'				: ['P:/z_to_archive/LEGO/TVC/03_LEGO FALL 2013/Lego_LOTR', 
	# 	{''							: False }],

	# 'Project_X' 					: ['P:/z_to_archive/PT_PROJECTS/Project_X', 
	# 	{''							: True }],
							
	# 'Lego_Superheroes'			: ['P:/z_to_archive/LEGO/TVC/03_LEGO FALL 2013/Lego_Superheroes', 
	# 	{'2013_Fall_SuperheroA' 	: False,
	# 	'2013_Fall_SuperheroB' 		: False }],

	# 'Lego_Chima'					: ['P:/z_to_archive/LEGO/TVC/03_LEGO FALL 2013/Lego_Chima', 
	# 	{'2013_Fall_SG' 			: False, 
	# 	'2013_Fall_LegendBeast' 	: False,
	# 	'2013_Fall_PT' 				: False, 
	# 	'2013_KingOfScorpion' 		: False,
	# 	'2013_LavalCragger' 		: False }],

	# 'Lego_FriendsX'				: ['P:/z_to_archive/LEGO/FRIENDS/Lego_FriendsX', 
	# 	{''							: True }],

	# 'Friends_Blooper' 			: ['P:/z_to_archive/LEGO/FRIENDS/Friends_Blooper', 
	# 	{''							: True }],
}


						

