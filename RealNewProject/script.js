// 🚨 여기에 본인의 넥슨 API 키를 입력하세요.
const API_KEY = "YOUR_NEXON_API_KEY";

// 어제 날짜를 YYYY-MM-DD 형식으로 가져오는 헬퍼 함수
// 메이플 API는 안정적인 조회를 위해 어제 날짜 기준을 권장합니다.
function getYesterdayDate() {
    const today = new Date();
    const yesterday = new Date(today.setDate(today.getDate() - 1));
    const yyyy = yesterday.getFullYear();
    const mm = String(yesterday.getMonth() + 1).padStart(2, '0');
    const dd = String(yesterday.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
}

// DOM 요소 가져오기
const searchButton = document.getElementById('searchButton');
const nicknameInput = document.getElementById('nicknameInput');
const loader = document.getElementById('loader');
const resultArea = document.getElementById('resultArea');
const errorArea = document.getElementById('errorArea');

// 검색 버튼 클릭 이벤트
searchButton.addEventListener('click', () => {
    const nickname = nicknameInput.value;
    if (!nickname) {
        showError('닉네임을 입력해주세요.');
        return;
    }
    searchCharacter(nickname);
});

// 에러 메시지 표시 함수
function showError(message) {
    errorArea.textContent = message;
    errorArea.classList.remove('hidden');
    resultArea.classList.add('hidden');
}

// 결과 표시 함수 (데이터 표시)
function displayData(basicInfo, equipmentInfo) {
    // 기본 정보
    document.getElementById('charImage').src = basicInfo.character_image;
    document.getElementById('charName').textContent = basicInfo.character_name;
    document.getElementById('charWorld').textContent = basicInfo.world_name;
    document.getElementById('charLevel').textContent = basicInfo.character_level;
    document.getElementById('charClass').textContent = basicInfo.character_class;

    // 장비 정보 (아이템 이름만 리스트로)
    const equipmentContainer = document.getElementById('equipmentInfo');
    equipmentContainer.innerHTML = ''; // 이전 결과 초기화
    const equipList = document.createElement('ul');
    
    equipmentInfo.item_equipment.forEach(item => {
        const li = document.createElement('li');
        li.textContent = `${item.item_equipment_part}: ${item.item_name}`;
        equipList.appendChild(li);
    });
    
    equipmentContainer.appendChild(equipList);

    // 결과 영역 보이기
    resultArea.classList.remove('hidden');
    errorArea.classList.add('hidden');
}


// 캐릭터 검색 메인 함수 (Async/Await 사용)
async function searchCharacter(nickname) {
    // 로딩 시작
    loader.classList.remove('hidden');
    resultArea.classList.add('hidden');
    errorArea.classList.add('hidden');

    const headers = {
        "x-nxopen-api-key": API_KEY
    };

    try {
        // 1. 닉네임으로 ocid (캐릭터 식별자) 조회
        const ocidResponse = await fetch(`https://open.api.nexon.com/maplestory/v1/id?character_name=${encodeURIComponent(nickname)}`, { headers });
        
        if (!ocidResponse.ok) {
            if (ocidResponse.status === 404) {
                throw new Error('캐릭터를 찾을 수 없습니다.');
            }
            throw new Error(`OCID 조회 실패: ${ocidResponse.statusText}`);
        }
        
        const ocidData = await ocidResponse.json();
        const ocid = ocidData.ocid;

        // 2. 어제 날짜 기준 데이터 조회
        const date = getYesterdayDate();

        // 3. ocid로 기본 정보 조회
        const basicInfoPromise = fetch(`https://open.api.nexon.com/maplestory/v1/character/basic?ocid=${ocid}&date=${date}`, { headers })
            .then(res => res.json());

        // 4. ocid로 장비 정보 조회 (예시 "역사 정보")
        const equipmentInfoPromise = fetch(`https://open.api.nexon.com/maplestory/v1/character/item-equipment?ocid=${ocid}&date=${date}`, { headers })
            .then(res => res.json());

        // 5. 두 요청을 병렬로 처리하고 모두 기다림
        const [basicInfo, equipmentInfo] = await Promise.all([basicInfoPromise, equipmentInfoPromise]);

        // 6. 결과 표시
        displayData(basicInfo, equipmentInfo);

    } catch (error) {
        console.error('Error:', error);
        showError(error.message || '데이터를 불러오는 중 오류가 발생했습니다.');
    } finally {
        // 로딩 완료
        loader.classList.add('hidden');
    }
}
