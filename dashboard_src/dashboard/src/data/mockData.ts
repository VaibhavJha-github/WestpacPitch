export type Sentiment = 'Positive' | 'Neutral' | 'Anxious' | 'Frustrated';

export interface Message {
  id: string;
  sender: 'Bot' | 'Customer';
  text: string;
  timestamp: string;
}

export type LocationType = 'In-branch' | 'Mobile lender visit' | 'Video chat' | 'Phone';

export interface CollectedData {
  label: string;
  value?: string;
}



export interface Appointment {
  id: string;
  customerName: string;
  customerInitials: string;
  companyName?: string;
  time: string;
  date: string;
  type: string;
  locationType: LocationType;
  sentiment: Sentiment;
  sentimentScore: number;
  sentimentNote?: string;
  intent: string;
  aiNote: string;
  transcript: Message[];
  status: 'Upcoming' | 'Completed' | 'Cancelled';
  customerTenure?: string;
  age?: number;
  location?: string;
  profession?: string;
  totalBankingValue?: string;
  estimatedLoanSize?: string;
  currentLender?: string;
  reasonForLeaving?: string;
  selfDeclaredLVR?: string;
  collectedData?: CollectedData[];
  recommendedStrategy?: {
    title: string;
    description: string;
  };
}

export const appointments: Appointment[] = [
  {
    id: '1',
    customerName: 'Alice Nguyen',
    customerInitials: 'AN',
    time: '14:00',
    date: '2026-01-15',
    type: 'Refinance Discussion',
    locationType: 'Video chat',
    sentiment: 'Positive',
    sentimentScore: 92,
    intent: 'Refinance from External Lender',
    aiNote: 'Customer is rate-sensitive and has seen a competitor offer at CBA. Looking to fix for 3 years. Has strong deposit history ($85k) which makes her a good candidate for our offset package. Recommend leading with total value proposition rather than rate-matching alone.',
    status: 'Upcoming',
    customerTenure: '8 years',
    age: 38,
    location: 'Parramatta, NSW',
    profession: 'Marketing Manager',
    totalBankingValue: '$85,000 (Deposits)',
    estimatedLoanSize: '$650k',
    currentLender: 'Westpac',
    reasonForLeaving: 'Rate Competitiveness',
    selfDeclaredLVR: '~70%',
    collectedData: [
      { label: 'Loan Amount', value: '$650,000' },
      { label: 'Property Address', value: '42 Smith St, Parramatta' },
      { label: 'Annual Salary', value: '$125,000' },
      { label: 'Fixed Term Preference', value: '3 years' },
      { label: 'Competitor Offer', value: 'CBA (0.3% lower)' },
    ],
    recommendedStrategy: {
      title: 'Rate Match + Package Benefits',
      description: 'Lead with total value proposition — offset account benefits and package discounts. Verify current loan balance before quoting. She mentioned CBA offer, so be prepared to discuss rate matching.',
    },
    transcript: [
      { id: 'm1', sender: 'Bot', text: 'Hi there! Thanks for calling Westpac. My name is Alex, your virtual assistant. Can I start by getting your full name please?', timestamp: '09:58' },
      { id: 'm2', sender: 'Customer', text: 'Hi Alex, it\'s Alice Nguyen.', timestamp: '09:58' },
      { id: 'm3', sender: 'Bot', text: 'Thanks Alice. And just to verify your identity, could you please confirm your date of birth?', timestamp: '09:58' },
      { id: 'm4', sender: 'Customer', text: 'Sure, it\'s the 12th of March, 1988.', timestamp: '09:59' },
      { id: 'm5', sender: 'Bot', text: 'Perfect, thank you for confirming. I can see you\'ve been with Westpac for about 8 years — we really appreciate your loyalty! How can I help you today?', timestamp: '09:59' },
      { id: 'm6', sender: 'Customer', text: 'I need to speak with someone about my home loan. My fixed rate is ending next month and I want to discuss my options.', timestamp: '10:00' },
      { id: 'm7', sender: 'Bot', text: 'Of course, I can help arrange that. Just so our specialist can prepare the best options for you, would it be alright if I collect a few details first?', timestamp: '10:00' },
      { id: 'm8', sender: 'Customer', text: 'Yeah, that\'s fine.', timestamp: '10:01' },
      { id: 'm9', sender: 'Bot', text: 'Great, thank you. What\'s the property address for this loan?', timestamp: '10:01' },
      { id: 'm10', sender: 'Customer', text: 'It\'s 42 Smith Street in Parramatta.', timestamp: '10:01' },
      { id: 'm11', sender: 'Bot', text: 'Got it. And roughly what\'s the current loan amount?', timestamp: '10:02' },
      { id: 'm12', sender: 'Customer', text: 'About $650,000.', timestamp: '10:02' },
      { id: 'm13', sender: 'Bot', text: 'Thanks. Are you looking to stay on a fixed rate, or considering variable this time?', timestamp: '10:03' },
      { id: 'm14', sender: 'Customer', text: 'I\'d prefer to fix again, probably for another 3 years. I like knowing exactly what my repayments will be. To be honest, I\'ve been looking around and CBA sent me an offer that\'s about 0.3% lower than what I see on your website.', timestamp: '10:03' },
      { id: 'm15', sender: 'Bot', text: 'I appreciate you sharing that. To help our specialist look at the full picture, can I ask what your approximate annual income is?', timestamp: '10:04' },
      { id: 'm16', sender: 'Customer', text: 'Around $125,000 before tax. I\'m a marketing manager.', timestamp: '10:04' },
      { id: 'm17', sender: 'Bot', text: 'Thank you. I\'ve got all the details. Our home loan specialists will be able to discuss competitive options with you, especially given your history with us. What day works best for an appointment?', timestamp: '10:05' },
      { id: 'm18', sender: 'Customer', text: 'Thursday afternoon would be ideal, maybe around 2pm? I can do a video call from work.', timestamp: '10:05' },
      { id: 'm19', sender: 'Bot', text: 'Perfect. I\'ve booked you in for Thursday at 2pm via video chat. You\'ll receive a confirmation email shortly with the meeting link. Is there anything else I can help with today?', timestamp: '10:06' },
      { id: 'm20', sender: 'Customer', text: 'No, that\'s everything. Thanks for your help!', timestamp: '10:06' },
    ]
  },
  {
    id: '2',
    customerName: 'James & Emily Porter',
    customerInitials: 'JP',
    companyName: 'Tom & Jerry Animation Studio',
    time: '15:30',
    date: '2026-01-15',
    type: 'First Home Buyer Enquiry',
    locationType: 'In-branch',
    sentiment: 'Anxious',
    sentimentScore: 45,
    sentimentNote: 'Customers expressed concern about their fluctuating income affecting loan approval. They mentioned feeling "nervous" and "worried" multiple times during the call.',
    intent: 'First Home Purchase - Pre-approval',
    aiNote: 'First-time buyers who run a creative business together. Income fluctuates seasonally which is causing anxiety about approval. They have a solid deposit saved but are worried about rejection. Need reassurance about self-employed lending options.',
    status: 'Upcoming',
    customerTenure: 'New Customer',
    age: 32,
    location: 'Surry Hills, NSW',
    profession: 'Business Owners - Animation Studio',
    totalBankingValue: '$25,000 (Savings)',
    estimatedLoanSize: '$750k',
    currentLender: 'N/A',
    reasonForLeaving: 'N/A',
    selfDeclaredLVR: '~85%',
    collectedData: [
      { label: 'Business Trading', value: '4 years' },
      { label: 'Target Purchase Price', value: '$850,000' },
      { label: 'Deposit Saved', value: '$127,500' },
    ],
    recommendedStrategy: {
      title: 'Self-Employed Specialist Pathway',
      description: 'Reassure them about self-employed lending options — fluctuating income is normal for creative businesses. Will need 2 years of tax returns. Discuss LMI given their 15% deposit.',
    },
    transcript: [
      { id: 'm1', sender: 'Bot', text: 'Welcome to Westpac! I\'m your virtual assistant. Can I start by getting your name please?', timestamp: '14:22' },
      { id: 'm2', sender: 'Customer', text: 'Hi, I\'m James Porter, and my partner Emily is here with me too.', timestamp: '14:22' },
      { id: 'm3', sender: 'Bot', text: 'Hi James and Emily! Great to have you both. How can I help you today?', timestamp: '14:23' },
      { id: 'm4', sender: 'Customer', text: 'We\'re looking to buy our first home and we\'d like to book an appointment with someone to discuss our options.', timestamp: '14:23' },
      { id: 'm5', sender: 'Bot', text: 'Of course! I can arrange that for you. Just so our specialist can prepare for your meeting, would it be alright if I collect a few details first?', timestamp: '14:24' },
      { id: 'm6', sender: 'Customer', text: 'Sure, go ahead.', timestamp: '14:24' },
      { id: 'm7', sender: 'Bot', text: 'Great, thank you. What\'s the best contact number for you both?', timestamp: '14:25' },
      { id: 'm8', sender: 'Customer', text: 'You can reach us on 0412 345 678.', timestamp: '14:25' },
      { id: 'm9', sender: 'Bot', text: 'Perfect. Are you currently employed or self-employed?', timestamp: '14:26' },
      { id: 'm10', sender: 'Customer', text: 'We run our own business together — an animation studio. That\'s actually what we\'re a bit worried about.', timestamp: '14:26' },
      { id: 'm11', sender: 'Bot', text: 'Self-employed borrowers are very common, so don\'t worry. What\'s the name of your business?', timestamp: '14:27' },
      { id: 'm12', sender: 'Customer', text: 'It\'s called Tom & Jerry Animation Studio. Our ABN is 51 824 753 556 if you need that.', timestamp: '14:27' },
      { id: 'm13', sender: 'Bot', text: 'That\'s helpful, thank you. And how long has the business been operating?', timestamp: '14:28' },
      { id: 'm14', sender: 'Customer', text: 'About 4 years now. The last two years have been our best actually.', timestamp: '14:28' },
      { id: 'm15', sender: 'Bot', text: 'Four years is excellent. Do you have a rough idea of what price range you\'re looking at for properties?', timestamp: '14:29' },
      { id: 'm16', sender: 'Customer', text: 'We\'re looking at places around $850,000.', timestamp: '14:29' },
      { id: 'm17', sender: 'Bot', text: 'And how much have you saved for a deposit so far?', timestamp: '14:30' },
      { id: 'm18', sender: 'Customer', text: 'We\'ve managed to save about $127,500 — I know that\'s only about 15%. We\'re a bit nervous about whether that\'s enough, and our income fluctuates which worries us too.', timestamp: '14:30' },
      { id: 'm19', sender: 'Bot', text: 'A 15% deposit is a solid starting point. Our specialists can walk you through all the options including for self-employed borrowers. Would you prefer an in-branch, phone, or video appointment?', timestamp: '14:31' },
      { id: 'm20', sender: 'Customer', text: 'In-branch would be great — it feels less stressful for something this big. Surry Hills if possible, that\'s close to our studio.', timestamp: '14:31' },
      { id: 'm21', sender: 'Bot', text: 'No problem. I can book you in at Surry Hills. Would Thursday at 3:30pm work for you both?', timestamp: '14:32' },
      { id: 'm22', sender: 'Customer', text: 'That works perfectly. What should we bring?', timestamp: '14:32' },
      { id: 'm23', sender: 'Bot', text: 'Please bring your last two years of tax returns, recent business bank statements, ID for both of you, and any information about properties you\'re interested in. Don\'t worry if you don\'t have everything — we can work through it together.', timestamp: '14:33' },
      { id: 'm24', sender: 'Customer', text: 'Okay, we\'ll gather all that. Thanks so much — we were actually dreading making this call!', timestamp: '14:33' },
    ]
  },
  {
    id: '3',
    customerName: 'Sarah Jenkins',
    customerInitials: 'SJ',
    time: '09:30',
    date: '2026-01-16',
    type: 'General Banking',
    locationType: 'Phone',
    sentiment: 'Neutral',
    sentimentScore: 78,
    intent: 'Account Consolidation',
    aiNote: 'Long-term customer with multiple legacy accounts accumulated over 15 years. Wants to simplify her banking. Has significant deposits which makes her a candidate for premium product upgrade. Straightforward service request.',
    status: 'Upcoming',
    customerTenure: '15 years',
    age: 52,
    location: 'Mosman, NSW',
    profession: 'Retired Teacher',
    totalBankingValue: '$320,000 (Deposits)',
    collectedData: [
      { label: 'Number of Accounts', value: '6 accounts' },
      { label: 'Estimated Total Balance', value: '$320,000' },
      { label: 'Preferred Channel', value: 'Mobile app' },
    ],
    recommendedStrategy: {
      title: 'Simplification + Bonus Rate',
      description: 'Consolidate into eSaver with bonus rate. Check term deposit maturity dates before consolidating. Show her the mobile app features — her daughter has been helping her with it.',
    },
    transcript: [
      { id: 'm1', sender: 'Bot', text: 'Good morning! Thanks for calling Westpac. I\'m your virtual assistant. Can I start by getting your full name?', timestamp: '11:45' },
      { id: 'm2', sender: 'Customer', text: 'Hello. It\'s Sarah Jenkins.', timestamp: '11:45' },
      { id: 'm3', sender: 'Bot', text: 'Thanks Sarah. And to verify your identity, could you please confirm your date of birth?', timestamp: '11:46' },
      { id: 'm4', sender: 'Customer', text: '8th of July, 1974.', timestamp: '11:46' },
      { id: 'm5', sender: 'Bot', text: 'Perfect, thank you. How can I help you today?', timestamp: '11:47' },
      { id: 'm6', sender: 'Customer', text: 'I\'d like to book an appointment with someone. I have too many accounts and it\'s getting confusing to manage. I want to simplify things.', timestamp: '11:47' },
      { id: 'm7', sender: 'Bot', text: 'Of course, I can arrange that. Just so our team can prepare, would it be alright if I note down a couple of details first?', timestamp: '11:48' },
      { id: 'm8', sender: 'Customer', text: 'That\'s fine.', timestamp: '11:48' },
      { id: 'm9', sender: 'Bot', text: 'Great. What\'s the best phone number to reach you on?', timestamp: '11:49' },
      { id: 'm10', sender: 'Customer', text: '0433 221 876.', timestamp: '11:49' },
      { id: 'm11', sender: 'Bot', text: 'Thank you. And roughly how many accounts do you have with us?', timestamp: '11:50' },
      { id: 'm12', sender: 'Customer', text: 'I think about six? There\'s my everyday account, a couple of old savings accounts, a term deposit that matured last year, and I can\'t even remember what the others are for.', timestamp: '11:50' },
      { id: 'm13', sender: 'Bot', text: 'That\'s quite common for long-term customers like yourself. Do you have a rough idea of the total balance across all of them?', timestamp: '11:51' },
      { id: 'm14', sender: 'Customer', text: 'Probably around $320,000 all up, I think. I just want everything in one or two places where I can see it easily on the app. My daughter showed me how to use it.', timestamp: '11:51' },
      { id: 'm15', sender: 'Bot', text: 'That\'s a great goal. Our team can help you consolidate and show you how to get the most out of the mobile app. Would a phone appointment work, or would you prefer to come into a branch?', timestamp: '11:52' },
      { id: 'm16', sender: 'Customer', text: 'Phone is fine. I don\'t need to come in for something like this, do I?', timestamp: '11:52' },
      { id: 'm17', sender: 'Bot', text: 'Not at all! We can handle everything over the phone. How does Friday at 9:30am sound?', timestamp: '11:53' },
      { id: 'm18', sender: 'Customer', text: 'Friday works. I\'ll be home all morning. Thank you for making this easy.', timestamp: '11:53' },
    ]
  },
  {
    id: '4',
    customerName: 'Michael Chang',
    customerInitials: 'MC',
    companyName: 'Golden Dragon Restaurant',
    time: '11:00',
    date: '2026-01-16',
    type: 'Business Loan',
    locationType: 'Mobile lender visit',
    sentiment: 'Positive',
    sentimentScore: 88,
    sentimentNote: 'Customer is enthusiastic and confident about expansion. Used phrases like "business is booming" and "perfect timing". Very positive energy throughout the call.',
    intent: 'Business Expansion - Second Location',
    aiNote: 'Established restaurant owner with strong 8-year trading history looking to expand. Already has equity in existing property and existing Westpac relationship. High-value opportunity for business lending and merchant services cross-sell.',
    status: 'Upcoming',
    customerTenure: '5 years',
    age: 45,
    location: 'Chatswood, NSW',
    profession: 'Restaurant Owner',
    totalBankingValue: '$180,000 (Business + Personal)',
    estimatedLoanSize: '$400k',
    currentLender: 'Westpac',
    collectedData: [
      { label: 'Loan Amount Requested', value: '$400,000' },
      { label: 'Loan Purpose', value: 'Fitout + Equipment' },
      { label: 'Security Offered', value: 'Existing property equity' },
      { label: 'Property Value', value: '$1.2M' },
      { label: 'Outstanding Mortgage', value: '$300,000' },
      { label: 'Trading History', value: '8 years' },
    ],
    recommendedStrategy: {
      title: 'Business Growth Package',
      description: 'Strong equity position and trading history. Request latest BAS statements and confirm new premises lease. Good opportunity to cross-sell EFTPOS and merchant services for the new location.',
    },
    transcript: [
      { id: 'm1', sender: 'Bot', text: 'Good afternoon! Westpac Business Banking, I\'m your virtual assistant. Can I get your name please?', timestamp: '13:15' },
      { id: 'm2', sender: 'Customer', text: 'Hi there! Michael Chang. I need to speak with someone about a business loan — I\'m looking to expand.', timestamp: '13:15' },
      { id: 'm3', sender: 'Bot', text: 'That\'s exciting, congratulations! I can arrange that for you. Just so our specialist can come prepared, would it be alright if I collect a few details first?', timestamp: '13:16' },
      { id: 'm4', sender: 'Customer', text: 'Sure, no problem.', timestamp: '13:16' },
      { id: 'm5', sender: 'Bot', text: 'Great. Are you an existing Westpac business customer?', timestamp: '13:17' },
      { id: 'm6', sender: 'Customer', text: 'Yes, I\'ve had my business accounts with you for about 5 years now. Golden Dragon in Chatswood — maybe you\'ve seen it! Business has been booming.', timestamp: '13:17' },
      { id: 'm7', sender: 'Bot', text: 'Wonderful! And what\'s the ABN for Golden Dragon?', timestamp: '13:18' },
      { id: 'm8', sender: 'Customer', text: '23 456 789 012.', timestamp: '13:18' },
      { id: 'm9', sender: 'Bot', text: 'Perfect. How much are you looking to borrow for the expansion?', timestamp: '13:19' },
      { id: 'm10', sender: 'Customer', text: 'About $400,000. I\'ve found a great spot in Eastwood for a second location.', timestamp: '13:19' },
      { id: 'm11', sender: 'Bot', text: 'Great. And what would the loan be used for specifically?', timestamp: '13:20' },
      { id: 'm12', sender: 'Customer', text: 'Mainly the fitout and kitchen equipment. Also some working capital for the first few months.', timestamp: '13:20' },
      { id: 'm13', sender: 'Bot', text: 'That makes sense. Do you have any security you\'re planning to offer against the loan?', timestamp: '13:21' },
      { id: 'm14', sender: 'Customer', text: 'Yes, I own the property where my current restaurant is. There\'s quite a bit of equity in it now — I had it valued recently at about $1.2 million and I only owe about $300k on the mortgage.', timestamp: '13:21' },
      { id: 'm15', sender: 'Bot', text: 'That\'s a strong equity position. How long has Golden Dragon been operating?', timestamp: '13:22' },
      { id: 'm16', sender: 'Customer', text: 'Eight years now. Started from scratch and built it up.', timestamp: '13:22' },
      { id: 'm17', sender: 'Bot', text: 'Impressive. I\'ve got all the details. Would you like to meet with a business banking specialist? We can do in-branch, phone, or video — or we have mobile lenders who can come to you.', timestamp: '13:23' },
      { id: 'm18', sender: 'Customer', text: 'Could someone come to me? I\'m pretty busy with the restaurant.', timestamp: '13:23' },
      { id: 'm19', sender: 'Bot', text: 'Absolutely! Would a morning meeting work before your lunch rush?', timestamp: '13:24' },
      { id: 'm20', sender: 'Customer', text: 'That would be perfect. How about Friday around 11am? The kitchen is prepped by then.', timestamp: '13:24' },
      { id: 'm21', sender: 'Bot', text: 'Friday at 11am works great. I\'ll have a specialist come to Golden Dragon in Chatswood. They\'ll want to see your recent BAS statements and discuss the lease for the new premises.', timestamp: '13:25' },
      { id: 'm22', sender: 'Customer', text: 'I\'ll have everything ready. This is perfect timing — I\'ve been planning this for a while!', timestamp: '13:25' },
    ]
  }
];
