## 6. 구독 결제 시스템(Stripe) 연동 및 수익화

마이크로SaaS의 완성은 결국 지속 가능한 수익화다. 앞서 구축한 LLM 폴백 라우팅 시스템이 아무리 훌륭해도 사용자가 결제하고 권한을 부여받는 파이프라인이 막혀 있으면 사업이 성립하지 않는다. 

이 장에서는 전 세계 표준 결제 플랫폼인 Stripe를 이용해 월 구독 모델을 붙이고, 결제 즉시 API 사용 권한을 자동 해제하는 로직을 구현한다. 불필요한 복잡성은 빼고, 오늘 당장 서비스에 이식할 수 있는 실전 코드 위주로 진행한다.

---

### 1. Stripe 기본 설정 및 제품 등록

가장 먼저 할 일은 상품과 가격을 정의하는 것이다. 개발 환경(Test Mode)에서 먼저 테스트를 마친 뒤 Live 모드로 전환하는 것이 원칙이다.

1. **Stripe 계정 생성 및 API 키 발급**
   * [Stripe 공식 홈페이지](https://stripe.com) 가입 후 대시보드 우측 상단의 **Test mode** 토글을 켠다.
   * `Developers > API keys` 메뉴에서 `Secret key`(`sk_test_...`)와 `Publishable key`(`pk_test_...`)를 복사해 `.env` 파일에 저장한다.

2. **제품(Product) 및 가격(Price) 생성**
   * 대시보드에서 `Products > Add product`를 클릭한다.
   * **Name**: `LLM Router Pro Plan`
   * **Pricing**: `Standard pricing`, 가격 입력 (예: 월 $29), 주기: `Monthly`.
   * 생성 후 발급되는 가격 ID (`price_1Nt...`)를 복사한다. 이 값 역시 환경 변수로 관리한다.

```env
STRIPE_SECRET_KEY=sk_test_51...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_1Nt...
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

---

### 2. 월 구독 결제 플로우(Checkout) 구현

Next.js(또는 Node.js 백엔드)를 기준으로, 사용자가 '구독하기' 버튼을 눌렀을 때 Stripe Checkout 페이지로 리다이렉트하는 API를 만든다.

**백엔드 라우트 예시 (`/api/create-checkout-session`):**

```typescript
import { NextResponse } from 'next/server';
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2023-10-16',
});

export async function POST(req: Request) {
  try {
    const { userId, email } = await req.json();

    const session = await stripe.checkout.sessions.create({
      payment_method_types: ['card'],
      line_items: [
        {
          price: process.env.STRIPE_PRICE_ID,
          quantity: 1,
        },
      ],
      mode: 'subscription',
      success_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard?success=true`,
      cancel_url: `${process.env.NEXT_PUBLIC_APP_URL}/pricing?canceled=true`,
      customer_email: email,
      metadata: {
        userId, // 나중에 웹훅에서 매칭하기 위한 사용자 식별자
      },
    });

    return NextResponse.json({ url: session.url });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
```

---

### 3. 결제 완료 웹훅(Webhook)을 통한 API 권한 자동 부여

결제가 성공했다고 해서 프론트엔드에서 바로 권한을 주면 안 된다. 반드시 Stripe 서버가 보내주는 웹훅(Webhook)을 백엔드에서 수신하여 안전하게 데이터베이스를 업데이트해야 한다.

1. **로컬 테스트를 위한 Stripe CLI 설정**
   * 터미널에 `stripe listen --forward-to localhost:3000/api/webhook` 실행.
   * 출력되는 `whsec_...` 키를 `.env`의 `STRIPE_WEBHOOK_SECRET`에 입력한다.

2. **웹훅 핸들러 구현 (`/api/webhook`):**

```typescript
import { headers } from 'next/headers';
import { NextResponse } from 'next/server';
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2023-10-16',
});

const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET!;

export async function POST(req: Request) {
  const body = await req.text();
  const signature = headers().get('stripe-signature')!;

  let event: Stripe.Event;

  try {
    event = stripe.webhooks.constructEvent(body, signature, webhookSecret);
  } catch (err: any) {
    return NextResponse.json({ error: `Webhook Error: ${err.message}` }, { status: 400 });
  }

  // 구독 생성 또는 결제 성공 이벤트 처리
  if (event.type === 'checkout.session.completed') {
    const session = event.data.object as Stripe.Checkout.Session;
    const userId = session.metadata?.userId;
    const customerId = session.customer as string;
    const subscriptionId = session.subscription as string;

    // [실전 DB 작업] 사용자 테이블에 구독 정보 및 권한 업데이트
    // 예: await db.user.update({ where: { id: userId }, data: { plan: 'PRO', stripeCustomerId: customerId, subscriptionId, isActive: true } });
    console.log(`[성공] 사용자 ${userId}에게 Pro 플랜 권한이 부여되었습니다.`);
  }

  // 구독 해지 또는 결제 실패 이벤트 처리
  if (event.type === 'customer.subscription.deleted') {
    const subscription = event.data.object as Stripe.Subscription;
    
    // [실전 DB 작업] 권한 회수
    // 예: await db.user.update({ where: { subscriptionId: subscription.id }, data: { plan: 'FREE', isActive: false } });
    console.log(`[만료] 구독 ${subscription.id}이 해지되어 권한이 회수되었습니다.`);
  }

  return NextResponse.json({ received: true });
}
```

---

### 4. 무료 체험(Free Tier)과 유료 플랜 사용량 제한 로직

무분별한 API 호출을 막고 유료 전환을 유도하기 위해 미들웨어 레벨에서 사용량을 제한한다. 

* **Free Tier**: 월 1,000 토큰 또는 Ollama 로컬 모델 우선 사용(Groq 폴백 제한).
* **Pro Tier**: Groq 및 상용 API 무제한 폴백 라우팅 허용.

**사용량 체크 및 라우팅 가드 미들웨어 템플릿:**

```typescript
// 유저의 플랜 상태와 이번 달 사용량을 확인하는 함수
async function checkUserQuota(userId: string): Promise<boolean> {
  const user = await db.user.findUnique({ where: { id: userId } });

  if (!user) return false;

  // 유료 사용자인 경우 통과
  if (user.isActive && user.plan === 'PRO') {
    return true;
  }

  // 무료 사용자인 경우 이번 달 사용량 체크 (예: 50회 제한)
  const currentUsage = await db.apiLog.count({
    where: {
      userId,
      createdAt: { gte: new Date(new Date().getFullYear(), new Date().getMonth(), 1) },
    },
  });

  if (currentUsage >= 50) {
    throw new Error('FREE_TIER_EXCEEDED: 무료 사용량 초과. Pro 플랜을 구독하세요.');
  }

  return true;
}
```

---

### 체크리스트: 실전 런칭 전 확인 사항

- [ ] Stripe 대시보드에서 웹훅 엔드포인트가 정확히 등록되었는가?
- [ ] 결제 취소 시 사용자가 깔끔하게 원래 페이지로 돌아오는가?
- [ ] `checkout.session.completed` 이벤트가 발생했을 때 DB에 유저 권한이 정확히 업데이트되는지 로그로 확인했는가?
- [ ] 무료 플랜 유저가 한도를 초과했을 때 명확한 에러 메시지와 함께 결제 페이지 링크가 안내되는가?

여기까지 완료했다면 1인 개발자로서 갖추어야 할 기본 인프라(AI 라우팅 + 자동 예외 처리 + 구독 결제)의 뼈대가 모두 완성된 것이다. 다음 장에서는 사용자를 모으기 위한 최소한의 랜딩페이지 구성과 SEO 최적화 전략을 다룬다.
