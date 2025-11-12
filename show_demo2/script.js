// 课程数据配置
const courseData = [
    {
        id: 1,
        title: "第一讲:M09个性化首饰设计及制作",
        slideContent: `
            <img src="slides/slide_001.png" style="max-width: 100%; height: auto;" alt="课程介绍">
        `,
        videoUrl: "videos/infinitetalk_res_480p_optimized_slide1.mp4",
        duration: "0:10",
        narration: "欢迎同学们选修制造工程体验课程M09：个性化首饰设计及制作。在这门课程中，你将学习首饰设计的基本原理，掌握3D建模和加工制作技能，亲手打造属于自己的独特作品。"
    },
    {
        id: 2,
        title: "第二讲:中心简介-历史沿革",
        slideContent: `
            <img src="slides/slide_002.png" style="max-width: 100%; height: auto;" alt="历史沿革">
        `,
        videoUrl: "videos/infinitetalk_res_480p_optimized_slide2.mp4",
        duration: "0:10",
        narration: "工训训练中心有着百年传承。从1921年的手工教学到金工实习，再到工训文化和工创理念，中心不断发展演进。如今，我们已经完成了从机械化、电气化到信息化、智能化的转型升级，始终走在工程教育创新的前沿。"
    },
    {
        id: 3,
        title: "第三讲:中心简介-功能定位",
        slideContent: `
            <img src="slides/slide_003.png" style="max-width: 100%; height: auto;" alt="功能定位">
        `,
        videoUrl: "videos/infinitetalk_res_480p_optimized_slide3.mp4", // 替换为您的视频URL
        duration: "0:10",
        narration: "清华大学基础工业训练中心，简称工训训练中心，是国际领先的工程实践与创新教育中心。中心传承工匠精神，弘扬创客文化，致力于培养学生的工程能力、劳动素质和创新创业能力，为同学们的梦想实现提供全方位支持。"
    }
];


// 全局状态
let currentSlideIndex = 0;
let completedSlides = new Set();
let slideNotes = {};
let isDragging = false;
let isResizing = false;
let startX, startY, startWidth, startHeight;
let pipVideoSize = 'medium'; // 默认中等大小

// DOM 元素
const currentSlideEl = document.getElementById('current-slide');
const slideCounter = document.getElementById('slide-counter');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const lectureVideo = document.getElementById('lecture-video');
const pipVideo = document.getElementById('pip-video');
const autoPlayCheckbox = document.getElementById('auto-play');
const speedControl = document.getElementById('speed-control');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const outlineList = document.getElementById('outline-list');
const notesTextarea = document.getElementById('notes');
const saveNotesBtn = document.getElementById('save-notes');
const dragHandle = document.getElementById('drag-handle');
const sizeButtons = document.querySelectorAll('.size-btn');

// 初始化
function init() {
    loadSlide(0);
    generateOutline();
    loadProgress();
    setupEventListeners();
    loadNotes();
    loadVideoSize();
}

// 加载幻灯片
function loadSlide(index) {
    if (index < 0 || index >= courseData.length) return;
    
    currentSlideIndex = index;
    const slide = courseData[index];
    
    // 更新幻灯片内容
    currentSlideEl.innerHTML = slide.slideContent;
    
    // 更新视频
    lectureVideo.src = slide.videoUrl;

    // 自动播放视频
    if (autoPlayCheckbox.checked) {
        lectureVideo.play().catch(err => {
            console.log('自动播放被阻止，请手动播放');
        });
    }
    
    // 更新计数器
    slideCounter.textContent = `${index + 1} / ${courseData.length}`;
    
    // 更新按钮状态
    prevBtn.disabled = index === 0;
    nextBtn.disabled = index === courseData.length - 1;
    
    // 标记为已完成
    completedSlides.add(index);
    
    // 更新进度
    updateProgress();
    
    // 更新大纲高亮
    updateOutlineHighlight();
    
    // 加载当前页笔记
    loadNotes();
    
    // 保存进度到 localStorage
    saveProgress();
}

// 生成课程大纲
function generateOutline() {
    outlineList.innerHTML = '';
    courseData.forEach((slide, index) => {
        const li = document.createElement('li');
        li.textContent = slide.title;
        li.dataset.index = index;
        li.addEventListener('click', () => loadSlide(index));
        outlineList.appendChild(li);
    });
}

// 更新大纲高亮
function updateOutlineHighlight() {
    const items = outlineList.querySelectorAll('li');
    items.forEach((item, index) => {
        item.classList.remove('active');
        if (index === currentSlideIndex) {
            item.classList.add('active');
        }
        if (completedSlides.has(index)) {
            item.classList.add('completed');
        }
    });
}

// 更新进度
function updateProgress() {
    const progress = (completedSlides.size / courseData.length) * 100;
    progressFill.style.width = `${progress}%`;
    progressText.textContent = `${completedSlides.size}/${courseData.length}`;
}

// 更新视频大小
function updateVideoSize(size) {
    pipVideoSize = size;
    pipVideo.className = 'pip-video-container size-' + size;
    
    // 更新按钮状态
    sizeButtons.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.size === size) {
            btn.classList.add('active');
        }
    });
    
    // 保存设置
    localStorage.setItem('pipVideoSize', size);
}

// 加载视频大小
function loadVideoSize() {
    const savedSize = localStorage.getItem('pipVideoSize');
    if (savedSize) {
        updateVideoSize(savedSize);
    }
}

// 画中画拖动功能
function setupDragging() {
    let offsetX, offsetY;
    
    pipVideo.addEventListener('mousedown', (e) => {
        // 如果点击的是视频控件或拖动手柄，不触发拖动
        if (e.target === lectureVideo || e.target.closest('.drag-handle')) return;
        
        if (pipVideo.classList.contains('minimized')) return;
        isDragging = true;
        offsetX = e.clientX - pipVideo.offsetLeft;
        offsetY = e.clientY - pipVideo.offsetTop;
        pipVideo.style.cursor = 'grabbing';
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        
        const slideWrapper = document.querySelector('.slide-wrapper');
        const rect = slideWrapper.getBoundingClientRect();
        
        let newLeft = e.clientX - rect.left - offsetX;
        let newTop = e.clientY - rect.top - offsetY;
        
        // 边界限制
        newLeft = Math.max(0, Math.min(newLeft, rect.width - pipVideo.offsetWidth));
        newTop = Math.max(0, Math.min(newTop, rect.height - pipVideo.offsetHeight));
        
        pipVideo.style.left = newLeft + 'px';
        pipVideo.style.top = newTop + 'px';
        pipVideo.style.right = 'auto';
        pipVideo.style.bottom = 'auto';
    });
    
    document.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            pipVideo.style.cursor = 'default';
        }
    });
}

// 设置事件监听
function setupEventListeners() {
    prevBtn.addEventListener('click', () => loadSlide(currentSlideIndex - 1));
    nextBtn.addEventListener('click', () => loadSlide(currentSlideIndex + 1));
    
    speedControl.addEventListener('change', (e) => {
        lectureVideo.playbackRate = parseFloat(e.target.value);
    });
    
    saveNotesBtn.addEventListener('click', saveNotes);
    
    // 视频大小按钮
    sizeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            updateVideoSize(btn.dataset.size);
        });
    });
    
    // 设置拖动
    setupDragging();
    
    // 键盘快捷键
    document.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowLeft') {
            loadSlide(currentSlideIndex - 1);
        } else if (e.key === 'ArrowRight') {
            loadSlide(currentSlideIndex + 1);
        } else if (e.key === ' ') {
            e.preventDefault();
            if (lectureVideo.paused) {
                lectureVideo.play();
            } else {
                lectureVideo.pause();
            }
        }
    });
}

// 保存笔记
function saveNotes() {
    const noteContent = notesTextarea.value;
    slideNotes[currentSlideIndex] = noteContent;
    localStorage.setItem('courseNotes', JSON.stringify(slideNotes));
    
    // 显示保存成功提示
    saveNotesBtn.textContent = '✓ 已保存';
    setTimeout(() => {
        saveNotesBtn.textContent = '保存笔记';
    }, 2000);
}

// 加载笔记
function loadNotes() {
    const savedNotes = localStorage.getItem('courseNotes');
    if (savedNotes) {
        slideNotes = JSON.parse(savedNotes);
    }
    notesTextarea.value = slideNotes[currentSlideIndex] || '';
}

// 保存进度
function saveProgress() {
    localStorage.setItem('courseProgress', JSON.stringify({
        currentSlide: currentSlideIndex,
        completedSlides: Array.from(completedSlides)
    }));
}

// 加载进度
function loadProgress() {
    const savedProgress = localStorage.getItem('courseProgress');
    if (savedProgress) {
        const progress = JSON.parse(savedProgress);
        completedSlides = new Set(progress.completedSlides);
        updateProgress();
        updateOutlineHighlight();
    }
}

// 启动应用
init();