import streamlit as st


def calculate_expert_price(cost_val, cost_unit, weight_g, dims, profit_val, profit_unit, ship_rate, category_config,
                           risk_buffer):
    cny_to_usd_safe = 7.1  # 汇率安全垫

    # 1. 统一转美金
    cost_usd = cost_val / cny_to_usd_safe if cost_unit == "CNY" else cost_val
    profit_usd = profit_val / cny_to_usd_safe if profit_unit == "CNY" else profit_val

    # 2. 处理不规则物体的“外接矩形”体积重
    l, w, h = dims
    # 针对不规则物体（如衣服蓬松、手办外箱），建议在长宽高各加 1.5cm 的包材厚度
    volumetric_weight = ((l + 1.5) * (w + 1.5) * (h + 1.5)) / 6000 * 1000
    billable_weight = max(weight_g, volumetric_weight)

    # 3. 运费计算
    shipping_usd = (billable_weight / 1000) * ship_rate

    # 4. 获取类目佣金
    commission = category_config['comm']

    # 5. 核心定价公式
    denominator = 1 - commission - risk_buffer
    price_trial = (cost_usd + shipping_usd + profit_usd) / denominator

    # 6. 美客多 299 MXN (约 17.5 USD) 固定费判定
    if price_trial < 17.5:
        final_price_usd = (cost_usd + shipping_usd + profit_usd + 1.8) / denominator
    else:
        final_price_usd = price_trial

    return final_price_usd, billable_weight, volumetric_weight


# --- UI 配置 ---
st.set_page_config(page_title="美客多全类目定价器", layout="wide")
st.title("🏆 美客多全类目专业定价工具")

# 类目预设库（佣金参考美客多跨境 CBT 标准）
CATEGORY_MAP = {
    "普通家居/3C配件 (19%)": {"comm": 0.19, "note": "适用于手机壳、餐垫、数据线等"},
    "服装/鞋靴/时尚 (22.5%)": {"comm": 0.225, "note": "衣服由于退换率高，佣金和损耗通常较高"},
    "玩具/手办/模型 (18%)": {"comm": 0.18, "note": "手办注意体积重，容易产生大包费用"},
    "运动户外 (19.5%)": {"comm": 0.195, "note": "适用于骑行装备、健身器材"},
    "自定义类目": {"comm": 0.19, "note": "手动微调佣金比例"}
}

with st.sidebar:
    st.header("1️⃣ 类目与风险设置")
    cate_choice = st.selectbox("选择产品类目", list(CATEGORY_MAP.keys()))
    current_cate = CATEGORY_MAP[cate_choice]
    st.caption(f"💡 {current_cate['note']}")

    # 如果选自定义，允许手动调
    if cate_choice == "自定义类目":
        final_comm = st.slider("手动调节佣金 (%)", 10.0, 30.0, 19.0) / 100
    else:
        final_comm = current_cate['comm']
        st.write(f"当前固定佣金: {final_comm * 100}%")

    risk_buffer = st.slider("风险备用金 (%)", 1.0, 15.0, 5.0, help="包含提现手续费、退货损耗、汇率波动") / 100

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.header("2️⃣ 成本与规格")
    c1, c2 = st.columns(2)
    with c1:
        c_unit = st.radio("成本币种", ["CNY", "USD"], horizontal=True)
        c_val = st.number_input("货源价格", value=15.88)
    with c2:
        p_unit = st.radio("利润币种", ["CNY", "USD"], horizontal=True)
        p_val = st.number_input("目标净利", value=30.0)

    st.subheader("📦 物理参数 (针对不规则物体)")
    w_g = st.number_input("实测重量 (g)", value=200.0)
    st.write("请输入包含外包装的最大外径：")
    l_col, w_col, h_col = st.columns(3)
    c_l = l_col.number_input("长 (cm)", value=10.0)
    c_w = w_col.number_input("宽 (cm)", value=10.0)
    c_h = h_col.number_input("高 (cm)", value=10.0)

    ship_rate = st.number_input("运费单价 (USD/KG)", value=16.0, help="墨西哥通常在 14-18 之间")

# --- 计算结果 ---
res_usd, b_weight, v_weight = calculate_expert_price(
    c_val, c_unit, w_g, (c_l, c_w, c_h), p_val, p_unit, ship_rate, {"comm": final_comm}, risk_buffer
)

with col2:
    st.header("3️⃣ 最终报价")
    res_mxn = res_usd * 17.2  # 实时比索汇率参考

    st.metric("美金标价 (USD)", f"${res_usd:.2f}")
    st.metric("预计墨西哥售价 (MXN)", f"${res_mxn:.2f}")

    # 关键预警
    if v_weight > w_g:
        st.error(f"🚨 警告：检测到该产品为“抛货”！体积重 ({v_weight:.0f}g) 远超实重。")
        st.caption("建议：衣服请尽量使用真空袋，手办尽量紧凑包装。")

    if res_usd < 17.5:
        st.warning("⚠️ 触发低价处罚：已自动加收 $1.8 手续费。")
    else:
        st.success("✅ 利润优化：已跨过 299 MXN 门槛，免除固定费。")

    st.markdown(f"""
    **成本拆解：**
    - 货源成本: ${c_val / 7.2 if c_unit == 'CNY' else c_val:.2f}
    - 预估运费: ${((b_weight / 1000) * ship_rate):.2f}
    - 平台佣金: ${(res_usd * final_comm):.2f}
    - 风险冗余: ${(res_usd * risk_buffer):.2f}
    """)